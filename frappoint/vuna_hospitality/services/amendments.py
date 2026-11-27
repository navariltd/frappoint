"""Amend a stay before arrival: new dates, room type, rate plan, or number of guests (design §11).

An amendment is the hold done again for the stay it already is, in one transaction:

1. the stay's rooms are given back;
2. the new details are quoted with the same checks as a new booking (booking window, restrictions
   with an authorized override, child ages, capacity);
3. the new rooms are taken under the inventory lock: a full night refuses the amendment, and
   because it all happens in one transaction the old rooms are never lost;
4. the nights are priced again at the current rates (`create_rate_nights` reuses the nights the
   stay already had), and the policies follow the rate plan;
5. a room assigned before arrival is kept if it still fits (same type, free for the new dates),
   otherwise it is taken off and the stay goes back to the unassigned list.

In-house stays don't use this: their departure changes through `front_desk.change_departure`,
and a different room is a room move.
"""

import frappe
from frappe import _
from frappe.utils import cint, getdate

from frappoint.vuna_hospitality.services import folio, inventory, notifications
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.money import from_minor
from frappoint.vuna_hospitality.services.reservations import (
	MEMBERSHIP,
	OCCUPANCY,
	POLICY_FIELDS,
	SERVICE_FLAG,
	STAY,
	_cancel_pending_nights,
	_get_open_property,
	_limits,
	_lock_stay,
	_override_fields,
	_policy_snapshot,
	_prepare_stay,
	create_rate_nights,
	refresh_booking,
)
from frappoint.vuna_hospitality.services.status_commands import transition

AMENDABLE = ("Held", "Confirmed", "Due In")
FIELDS = ("arrival_date", "departure_date", "room_type", "rate_plan", "adults", "children", "total_amount")


class AmendmentError(frappe.ValidationError):
	pass


def amend_stay(
	stay_name: str,
	arrival=None,
	departure=None,
	room_type: str | None = None,
	rate_plan: str | None = None,
	adults: int | None = None,
	children: int | None = None,
	child_ages: list | None = None,
	restriction_override_reason: str | None = None,
) -> dict:
	"""Change a stay that hasn't arrived. Anything left out stays as it is. Returns what changed."""
	stay = _lock_stay(stay_name)
	if stay.status not in AMENDABLE:
		frappe.throw(
			_(
				"Stay {0} is {1}. Only stays that haven't arrived are amended; an in-house stay changes its departure or moves room."
			).format(stay.name, _(stay.status)),
			AmendmentError,
		)
	wanted = frappe._dict(
		arrival=getdate(arrival or stay.arrival_date),
		departure=getdate(departure or stay.departure_date),
		room_type=room_type or stay.room_type,
		rate_plan=rate_plan or stay.rate_plan,
		adults=cint(adults) if adults not in (None, "") else cint(stay.adults),
		children=cint(children) if children not in (None, "") else cint(stay.children),
	)
	before = {field: stay.get(field) for field in FIELDS}
	if (
		wanted.arrival == getdate(stay.arrival_date)
		and wanted.departure == getdate(stay.departure_date)
		and wanted.room_type == stay.room_type
		and wanted.rate_plan == stay.rate_plan
		and wanted.adults == cint(stay.adults)
		and wanted.children == cint(stay.children)
		and child_ages is None
	):
		frappe.throw(_("Nothing to change."), AmendmentError)
	_check_guests(stay, wanted)

	kind = inventory.HELD if stay.status == "Held" else inventory.SOLD
	# Give the rooms back, then quote and take the new ones: a refusal rolls the whole request back.
	inventory.release(stay.room_type, stay.arrival_date, stay.departure_date, kind=kind)
	_cancel_pending_nights(stay.name)
	prop = _get_open_property(stay.property)
	prepared = _prepare_stay(
		stay.property,
		prop,
		_limits(),
		{
			"room_type": wanted.room_type,
			"rate_plan": wanted.rate_plan,
			"arrival": wanted.arrival,
			"departure": wanted.departure,
			"lead_guest": stay.lead_guest,
			"adults": wanted.adults,
			"children": wanted.children,
			"child_ages": child_ages
			if child_ages is not None
			else frappe.parse_json(stay.child_ages or "null"),
			"restriction_override_reason": restriction_override_reason,
		},
		amendment=True,
	)
	inventory.acquire(prepared.room_type, prepared.arrival, prepared.departure, kind=kind)
	quote = prepared.quote
	create_rate_nights(stay.property, stay.name, quote)

	frappe.db.set_value(
		OCCUPANCY,
		stay.room_occupancy,
		{
			"room_type": quote.room_type,
			"start_date": prepared.arrival,
			"end_date": prepared.departure,
			"adults": quote.adults,
			"children": quote.children,
		},
	)
	for membership in frappe.get_all(MEMBERSHIP, filters={"stay_reservation": stay.name}, pluck="name"):
		frappe.db.set_value(
			MEMBERSHIP, membership, {"start_date": prepared.arrival, "end_date": prepared.departure}
		)

	room_kept = _keep_or_release_room(stay, prepared)
	_move_guest_windows(stay, prepared)
	stay.flags[SERVICE_FLAG] = True
	stay.update(
		{
			"arrival_date": prepared.arrival,
			"departure_date": prepared.departure,
			"nights": len(quote.nights),
			"room_type": quote.room_type,
			"rate_plan": quote.rate_plan,
			"adults": quote.adults,
			"children": quote.children,
			"child_ages": frappe.as_json(quote.child_ages) if quote.child_ages else None,
			"total_amount": quote.total,
			"average_rate": from_minor(quote.total_minor // max(len(quote.nights), 1), quote.currency),
			**{field: prepared.policies.get(field) for field in POLICY_FIELDS},
			**{
				f"{field}_snapshot": _policy_snapshot(prepared.policies.get(field)) for field in POLICY_FIELDS
			},
			**_override_fields(prepared),
		}
	)
	stay.save(ignore_permissions=True)
	after = {field: stay.get(field) for field in FIELDS}
	log_event(
		STAY,
		stay.name,
		"Stay Amended",
		reason=prepared.override_reason,
		data={"before": before, "after": after, "room_kept": room_kept},
	)
	folio.refresh_stay_pending(stay.name)
	refresh_booking(stay.hotel_booking)
	notifications.notify(
		notifications.BOOKING_AMENDED,
		stay=stay.name,
		occurrence=f"amend:{prepared.arrival}:{prepared.departure}:{quote.room_type}:{quote.rate_plan}:{quote.adults}:{quote.children}",
	)
	return {"stay": stay.name, "before": before, "after": after, "room_kept": room_kept}


def _check_guests(stay, wanted) -> None:
	"""The new numbers can't be fewer than the guests already on the stay."""
	from frappoint.vuna_hospitality.services.front_desk import ADULT, active_guests

	guests = active_guests(stay.name)
	adults = sum(guest.age_category == ADULT for guest in guests)
	children = len(guests) - adults
	if wanted.adults < max(adults, 1) or wanted.children < children:
		frappe.throw(
			_(
				"The stay already has {0} adult(s) and {1} child(ren). Remove guests first, then amend."
			).format(adults, children),
			AmendmentError,
		)


def _move_guest_windows(stay, prepared) -> None:
	from frappoint.vuna_hospitality.services import front_desk

	start, end = front_desk.stay_window(stay, prepared.arrival, prepared.departure)
	for guest in front_desk.active_guests(stay.name):
		frappe.db.set_value(
			front_desk.STAY_GUEST, guest.name, {"expected_arrival": start, "expected_departure": end}
		)


def _keep_or_release_room(stay, prepared) -> bool:
	"""Keep the assigned room when it is the same type and free for the new dates; otherwise take
	it off (the stay goes back to the unassigned list)."""
	from frappoint.vuna_hospitality.services import front_desk

	assignment = front_desk.current_assignment(stay.room_occupancy)
	if not assignment or assignment.status != "Assigned":
		return False
	start, end = front_desk.stay_window(stay, prepared.arrival, prepared.departure)
	turnover = frappe.db.get_value("Hotel Property", stay.property, "turnover_minutes")
	fits = (
		frappe.db.get_value("Hotel Room", assignment.hotel_room, "room_type") == prepared.room_type
		and not front_desk.find_conflict(assignment.hotel_room, start, end, turnover, stay.room_occupancy)
		and not front_desk.room_closed(assignment.hotel_room, prepared.arrival, prepared.departure)
	)
	if fits:
		frappe.db.set_value(
			front_desk.ASSIGNMENT,
			assignment.name,
			{
				"start_date": prepared.arrival,
				"end_date": prepared.departure,
				"start_datetime": start,
				"end_datetime": end,
			},
		)
		return True
	if assignment.do_not_move:
		frappe.throw(
			_(
				"Room {0} is locked to this stay (Do Not Move) and doesn't fit the new details. Unlock it first."
			).format(assignment.room_number),
			AmendmentError,
		)
	transition(
		assignment,
		"Cancelled",
		reason=_("The stay was amended"),
		event_type="Room Unassigned",
		ignore_permissions=True,
	)
	return False
