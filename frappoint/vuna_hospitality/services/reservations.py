"""Booking, hold, and confirm (design §11, §28.4, §30.8-30.12; feature F5).

A Hotel Booking holds one or more Stay Reservations. Each stay puts demand on inventory through a
Room Occupancy, linked to the stay by an Occupancy Membership, and keeps its price as one Stay Rate
Night per night, copied from the quote.

Commands (every one runs in the caller's transaction and is safe to retry in a new one):

- `hold()`: quote, take the rooms as *held* under lock, and create the records, all at once.
- `confirm()`: turn the held rooms into *sold* rooms.
- `cancel()`: give the rooms back and charge the cancellation fee the stay was booked with (F12).
- `expire_hold()`: give back the rooms of a hold that ran out; `expire_holds()` is the job.
- `mark_no_show()`: night audit's no-show stage: give the rooms back and charge the no-show fee.
- `reinstate()`: bring a cancelled or no-show stay back, taking its rooms again under lock.

Every command locks the Stay Reservation row first, then the inventory rows, then the Hotel
Booking row. Locking in one order means a confirm and an expiry that race for the same hold run one
after the other, so the hold is released (or confirmed) exactly once.
"""

from collections import defaultdict
from datetime import date
from typing import cast

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, cint, get_datetime, getdate, now_datetime

from frappoint.vuna_hospitality.constants import FOLIO_MANAGER_ROLES, RESERVATION_MANAGER_ROLES
from frappoint.vuna_hospitality.services import inventory
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.feature_flag import hospitality_job
from frappoint.vuna_hospitality.services.money import from_minor, to_minor
from frappoint.vuna_hospitality.services.quote import SOLD_OUT, quote
from frappoint.vuna_hospitality.services.status_commands import InvalidTransitionError, transition

BOOKING = "Hotel Booking"
STAY = "Stay Reservation"
OCCUPANCY = "Room Occupancy"
MEMBERSHIP = "Occupancy Membership"
RATE_NIGHT = "Stay Rate Night"
SETTINGS = "Hospitality Settings"

HELD, CONFIRMED, CANCELLED, EXPIRED = "Held", "Confirmed", "Cancelled", "Expired"
RELEASED = "Released"
INACTIVE_STAY_STATUSES = (CANCELLED, EXPIRED)
CANCELLABLE_STAY_STATUSES = (HELD, CONFIRMED, "Due In")
ACTIVE_ALLOCATIONS = (HELD, CONFIRMED)
# A booking whose remaining stays are all finished is Closed.
FINISHED_STAY_STATUSES = ("Checked Out", "No Show")

DEFAULT_HOLD_MINUTES = 15
DEFAULT_MAX_STAY_NIGHTS = 30
# Booking sources are ERPNext UTM Sources. The first four use the names ERPNext's setup already
# creates, so sites don't end up with "Walk In" and "Walk-in" side by side.
DEFAULT_BOOKING_SOURCES = ("Walk In", "Phone Calls", "Emails", "Website", "Travel Agent", "Corporate")
UTM_SOURCE = "UTM Source"
EXPIRY_BATCH = 500

# Set on records created by this service; the DocTypes refuse inserts without it.
SERVICE_FLAG = "from_reservation_service"
POLICY_SNAPSHOT_FIELDS = (
	"name",
	"policy_name",
	"policy_type",
	"free_until_hours_before_arrival",
	"fee_type",
	"fee_value",
	"deposit_type",
	"deposit_value",
	"deposit_due_days_after_booking",
	"release_if_unpaid",
	"guest_text",
)


# The policies a stay copies from its rate plan when held (F5; no-show and early departure, F12).
POLICY_FIELDS = ("cancellation_policy", "deposit_policy", "no_show_policy", "early_departure_policy")


class HoldRefusedError(frappe.ValidationError):
	"""The stay can't be held: no quote, a closed date, or a restricted guest."""


class HoldExpiredError(frappe.ValidationError):
	"""The hold ran out before it was confirmed. Its rooms are released by the expiry job."""


# --------------------------------------------------------------------------- guards for DocTypes


def guard_service_insert(doc) -> None:
	"""Reservation records are created only by this service, so inventory always matches them."""
	if doc.is_new() and not doc.flags.get(SERVICE_FLAG):
		frappe.throw(
			_("{0} records are created from the booking desk, not entered directly.").format(_(doc.doctype))
		)


def guard_locked_fields(doc, fieldnames) -> None:
	"""Dates, room type and rate plan change only through amendment commands (not in F5)."""
	changed = [field for field in fieldnames if doc.has_value_changed(field)]
	if changed and not doc.flags.get(SERVICE_FLAG):
		frappe.throw(
			_("{0} cannot be edited on a saved stay: {1}.").format(
				_(doc.doctype), ", ".join(_(doc.meta.get_label(field)) for field in changed)
			)
		)


def _row(doctype: str, name: str, fields) -> frappe._dict:
	"""`frappe.db.get_value(..., as_dict=True)`, typed as the frappe._dict it returns (empty if none).

	`get_value` has no return annotation, so type checkers treat its result as a plain dict and
	reject attribute access such as `row.status`.
	"""
	return cast(frappe._dict, frappe.db.get_value(doctype, name, fields, as_dict=True) or frappe._dict())


def _new(doctype: str, values: dict):
	doc = frappe.get_doc({"doctype": doctype, **values})
	doc.flags[SERVICE_FLAG] = True
	return doc.insert(ignore_permissions=True)


# --------------------------------------------------------------------------- hold


def hold(
	property_name: str,
	stays: list[dict],
	booking: str | None = None,
	booking_details: dict | None = None,
) -> dict:
	"""Hold rooms for one or more stays on a new or existing booking: all of them or none.

	Each stay is a dict with `room_type`, `rate_plan`, `arrival`, `departure`, `lead_guest`, and
	optionally `adults`, `children`, `eta`, `etd`, `notes`. A new booking needs
	`booking_details["booking_source"]`. The held rooms are released if the hold isn't confirmed
	within Hospitality Settings' hold expiry. Returns the booking summary.
	"""
	if not stays:
		frappe.throw(_("Add at least one stay to hold."))

	prop = _get_open_property(property_name)
	limits = _limits()
	prepared = [_prepare_stay(property_name, prop, limits, stay) for stay in stays]

	# Take the rooms first: this locks the inventory rows and fails before anything is written.
	inventory.acquire_many(
		[
			{"room_type": p.room_type, "arrival": p.arrival, "departure": p.departure, "quantity": 1}
			for p in prepared
		],
		kind=inventory.HELD,
	)

	booking_doc = (
		_lock_booking(booking, property_name)
		if booking
		else _create_booking(property_name, booking_details or {})
	)
	expires_at = add_to_date(now_datetime(), minutes=limits.hold_minutes)
	for p in prepared:
		_create_stay(booking_doc, p, expires_at)

	refresh_booking(booking_doc.name)
	return booking_summary(booking_doc.name)


def _get_open_property(property_name: str):
	prop = _row("Hotel Property", property_name, ["name", "is_active", "business_date"])
	if not prop:
		frappe.throw(_("Hotel Property {0} does not exist.").format(property_name))
	if not prop.is_active:
		frappe.throw(_("Hotel Property {0} is inactive.").format(property_name))
	return prop


def _limits():
	settings = _row(
		SETTINGS, SETTINGS, ["hold_expiry_minutes", "max_stay_nights", "max_advance_booking_days"]
	)
	return frappe._dict(
		hold_minutes=cint(settings.hold_expiry_minutes) or DEFAULT_HOLD_MINUTES,
		max_stay_nights=cint(settings.max_stay_nights) or DEFAULT_MAX_STAY_NIGHTS,
		max_advance_days=cint(settings.max_advance_booking_days) or inventory.DEFAULT_HORIZON_DAYS,
	)


def _prepare_stay(property_name: str, prop, limits, stay: dict):
	stay = frappe._dict(stay)
	for field in ("room_type", "rate_plan", "arrival", "departure", "lead_guest"):
		if not stay.get(field):
			frappe.throw(_("Each stay needs {0}.").format(_(field.replace("_", " "))), HoldRefusedError)

	arrival, departure = getdate(stay.arrival), getdate(stay.departure)
	nights = inventory.nights_between(arrival, departure)
	business_date = getdate(prop.business_date)
	if arrival < business_date:
		frappe.throw(
			_("Arrival {0} is before the hotel's business date {1}.").format(
				frappe.format(arrival, "Date"), frappe.format(business_date, "Date")
			),
			HoldRefusedError,
		)
	if len(nights) > limits.max_stay_nights:
		frappe.throw(_("A stay can be at most {0} nights.").format(limits.max_stay_nights), HoldRefusedError)
	if arrival > add_days(business_date, limits.max_advance_days):
		frappe.throw(
			_("Bookings open only {0} days ahead.").format(limits.max_advance_days), HoldRefusedError
		)

	_check_lead_guest(stay.lead_guest)
	stay_quote = quote(
		property_name,
		arrival,
		departure,
		stay.room_type,
		stay.rate_plan,
		cint(stay.get("adults") or 1),
		cint(stay.get("children")),
		stay.get("child_ages"),
	)
	sold_out = next((night for night in stay_quote.nights if night.reason == SOLD_OUT), None)
	if sold_out:
		# The same error the inventory lock raises, so callers handle "sold out" one way.
		raise inventory.InventoryUnavailableError(
			_("{0} is sold out on {1}.").format(
				stay_quote.room_type_name, frappe.format(sold_out.night, "Date")
			),
			room_type=stay_quote.room_type,
			night=sold_out.night,
		)
	if not stay_quote.offered:
		frappe.throw(
			_("{0} on {1} can't be booked for these dates: {2}.").format(
				stay_quote.room_type_name,
				stay_quote.rate_plan_name,
				", ".join(_(reason) for reason in stay_quote.reasons),
			),
			HoldRefusedError,
		)

	policies = _row("Rate Plan", stay.rate_plan, POLICY_FIELDS)
	return frappe._dict(
		stay=stay,
		quote=stay_quote,
		room_type=stay_quote.room_type,
		arrival=arrival,
		departure=departure,
		policies=policies,
	)


def _check_lead_guest(guest_profile: str) -> None:
	guest = _row(
		"Guest Profile", guest_profile, ["full_name", "merged_into", "restriction_flag", "restriction_reason"]
	)
	if not guest:
		frappe.throw(_("Guest Profile {0} does not exist.").format(guest_profile), HoldRefusedError)
	if guest.merged_into:
		frappe.throw(
			_("Guest Profile {0} was merged into {1}. Use that profile instead.").format(
				guest_profile, guest.merged_into
			),
			HoldRefusedError,
		)
	if guest.restriction_flag:
		frappe.throw(
			_("{0} is marked Do Not Rent: {1}").format(
				frappe.bold(guest.full_name), guest.restriction_reason
			),
			HoldRefusedError,
		)


def _create_booking(property_name: str, details: dict):
	details = frappe._dict(details)
	if not details.booking_source:
		frappe.throw(_("Choose where the booking came from (Booking Source)."), HoldRefusedError)
	allowed = (
		"booking_source",
		"booker_guest_profile",
		"booker_customer",
		"market_segment",
		"sales_partner",
		"external_reference",
		"guarantee_type",
		"notes",
	)
	values = {field: details.get(field) for field in allowed if details.get(field)}
	if not values.get("sales_partner") and values.get("booker_customer"):
		# A customer booked through an agent or partner by default: ERPNext stores that on the Customer.
		values["sales_partner"] = frappe.db.get_value(
			"Customer", values["booker_customer"], "default_sales_partner"
		)
	booking = _new(BOOKING, {"property": property_name, "status": "Option", **values})
	log_event(BOOKING, booking.name, "Booking Created", to_status=booking.status, property_name=property_name)
	return booking


def _lock_booking(booking: str, property_name: str | None = None):
	_lock_row(BOOKING, booking)
	doc = frappe.get_doc(BOOKING, booking)
	if property_name and doc.property != property_name:
		frappe.throw(_("Hotel Booking {0} belongs to another property.").format(booking))
	if doc.status in ("Cancelled", "Closed"):
		frappe.throw(
			_("Hotel Booking {0} is {1}; stays can't be added to it.").format(booking, _(doc.status))
		)
	return doc


def _create_stay(booking, p, expires_at) -> str:
	q, stay = p.quote, p.stay
	adults, children = q.adults, q.children
	occupancy = _new(
		OCCUPANCY,
		{
			"property": booking.property,
			"hotel_booking": booking.name,
			"room_type": q.room_type,
			"start_date": p.arrival,
			"end_date": p.departure,
			"allocation_state": HELD,
			"hold_expires_at": expires_at,
			"adults": adults,
			"children": children,
		},
	)
	reservation = _new(
		STAY,
		{
			"property": booking.property,
			"hotel_booking": booking.name,
			"status": HELD,
			"hold_expires_at": expires_at,
			"lead_guest": stay.lead_guest,
			"adults": adults,
			"children": children,
			"child_ages": frappe.as_json(q.child_ages) if q.child_ages else None,
			"arrival_date": p.arrival,
			"departure_date": p.departure,
			"nights": len(q.nights),
			"room_type": q.room_type,
			"rate_plan": q.rate_plan,
			"room_occupancy": occupancy.name,
			"eta": stay.get("eta"),
			"etd": stay.get("etd"),
			"notes": stay.get("notes"),
			"currency": q.currency,
			"tax_inclusive": int(q.tax_inclusive),
			"total_amount": q.total,
			"average_rate": from_minor(q.total_minor // max(len(q.nights), 1), q.currency),
			**{field: p.policies.get(field) for field in POLICY_FIELDS},
			**{f"{field}_snapshot": _policy_snapshot(p.policies.get(field)) for field in POLICY_FIELDS},
		},
	)
	from frappoint.vuna_hospitality.services.front_desk import add_primary_guest

	add_primary_guest(reservation)
	_new(
		MEMBERSHIP,
		{
			"property": booking.property,
			"room_occupancy": occupancy.name,
			"stay_reservation": reservation.name,
			"start_date": p.arrival,
			"end_date": p.departure,
			"reason": "Initial",
		},
	)
	for night in q.nights:
		amount = from_minor(night.amount_minor, q.currency)
		components = [
			{**component, "amount": from_minor(component["amount_minor"], q.currency)}
			for component in night.components
		]
		_new(
			RATE_NIGHT,
			{
				"property": booking.property,
				"stay_reservation": reservation.name,
				"night_date": night.night,
				"rate_plan": q.rate_plan,
				"room_type": q.room_type,
				"adults": adults,
				"children": children,
				"currency": q.currency,
				"tax_inclusive": int(q.tax_inclusive),
				"room_rate": from_minor(night.room_rate_minor, q.currency),
				"extras_amount": from_minor(night.extras_minor, q.currency),
				"package_amount": from_minor(night.package_minor, q.currency),
				"total": amount,
				"components": frappe.as_json(components),
				"posting_state": "Pending",
			},
		)
	log_event(
		STAY,
		reservation.name,
		"Hold Placed",
		to_status=HELD,
		data={
			"booking": booking.name,
			"room_type": q.room_type,
			"rate_plan": q.rate_plan,
			"arrival": str(p.arrival),
			"departure": str(p.departure),
			"total": q.total,
			"hold_expires_at": str(expires_at),
		},
		property_name=booking.property,
	)
	return reservation.name


def _policy_snapshot(policy: str | None) -> str | None:
	if not policy:
		return None
	row = _row("Hotel Policy", policy, POLICY_SNAPSHOT_FIELDS)
	return frappe.as_json(row) if row else None


# --------------------------------------------------------------------------- confirm / cancel / expire


def confirm(stay_name: str) -> dict:
	"""Confirm a held stay: its rooms move from held to sold. Confirming twice changes nothing."""
	stay = _lock_stay(stay_name)
	if stay.status == CONFIRMED:
		return booking_summary(stay.hotel_booking)
	if stay.status != HELD:
		raise InvalidTransitionError(
			_("Stay {0} is {1} and can't be confirmed.").format(stay.name, _(stay.status))
		)
	if _hold_has_expired(stay):
		frappe.throw(
			_("The hold on stay {0} has expired. Search again and place a new hold.").format(stay.name),
			HoldExpiredError,
		)

	occupancy = frappe.get_doc(OCCUPANCY, stay.room_occupancy)
	inventory.convert(occupancy.room_type, occupancy.start_date, occupancy.end_date)
	transition(
		occupancy,
		CONFIRMED,
		updates={"hold_expires_at": None},
		event_type="Allocation Changed",
		ignore_permissions=True,
	)
	transition(
		stay,
		CONFIRMED,
		updates={
			"hold_expires_at": None,
			"confirmed_at": now_datetime(),
			"confirmed_by": frappe.session.user,
		},
		event_type="Reservation Confirmed",
		ignore_permissions=True,
	)
	from frappoint.vuna_hospitality.services.deposits import create_for_stay
	from frappoint.vuna_hospitality.services.folio import ensure_default_folio

	ensure_default_folio(stay.name)
	# The deposit the policy asks for (F12), on the default folio.
	create_for_stay(stay.name)
	refresh_booking(stay.hotel_booking)
	return booking_summary(stay.hotel_booking)


def confirm_booking(booking: str) -> dict:
	"""Confirm every held stay on the booking."""
	for name in _stays_of(booking, (HELD,)):
		confirm(name)
	return booking_summary(booking)


def cancel(
	stay_name: str,
	reason: str,
	*,
	waive_fee: bool = False,
	waive_reason: str | None = None,
	charge_fee: bool = True,
) -> dict:
	"""Cancel a held or confirmed stay and give its rooms back. Cancelling twice changes nothing.

	A confirmed stay cancelled inside its policy's penalty window is charged the cancellation fee
	(F12); a Front Desk Manager may `waive_fee` with a reason. A deposit pays the fee and only the
	excess is refunded. `charge_fee=False` is for the system releasing an unpaid deposit's stay.
	"""
	stay = _lock_stay(stay_name)
	if stay.status == CANCELLED:
		return booking_summary(stay.hotel_booking)
	if stay.status not in CANCELLABLE_STAY_STATUSES:
		raise InvalidTransitionError(
			_("Stay {0} is {1} and can't be cancelled.").format(stay.name, _(stay.status))
		)
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for cancelling stay {0}.").format(stay.name))

	from frappoint.vuna_hospitality.services import policies

	if charge_fee and stay.status != HELD:
		# Worked out from the nights given up, so before they are cancelled.
		policies.post_fee(stay, policies.CANCELLATION, waive=waive_fee, waive_reason=waive_reason)
	_release_occupancy(stay.room_occupancy, CANCELLED)
	_cancel_room_assignment(stay)
	transition(
		stay,
		CANCELLED,
		reason=reason,
		updates={
			"hold_expires_at": None,
			"cancelled_at": now_datetime(),
			"cancelled_by": frappe.session.user,
			"cancellation_reason": reason,
		},
		event_type="Reservation Cancelled",
		ignore_permissions=True,
	)
	_cancel_pending_nights(stay.name)
	from frappoint.vuna_hospitality.services.folio import close_idle_folios, refresh_stay_pending

	# A folio with charges (a fee, a posted extra) stays open for settlement.
	refresh_stay_pending(stay.name)
	_settle_deposit(stay.name, reason)
	close_idle_folios(stay.name, reason=reason)
	refresh_booking(stay.hotel_booking)
	return booking_summary(stay.hotel_booking)


def cancel_booking(
	booking: str, reason: str, *, waive_fee: bool = False, waive_reason: str | None = None
) -> dict:
	"""Cancel every held or confirmed stay on the booking."""
	for name in _stays_of(booking, CANCELLABLE_STAY_STATUSES):
		cancel(name, reason, waive_fee=waive_fee, waive_reason=waive_reason)
	return booking_summary(booking)


def _settle_deposit(stay_name: str, reason: str) -> None:
	"""The deposit pays the fee; the excess goes back (F12). What can't finish now is logged."""
	from frappoint.vuna_hospitality.services.deposits import settle_after_fee

	result = settle_after_fee(stay_name, reason)
	if result and (result.get("refund_waiting") or result.get("owing")):
		log_event(STAY, stay_name, "Deposit Follow-up", data=result)


# --------------------------------------------------------------------------- no-show and reinstatement


def mark_no_show(stay_name: str, business_date) -> bool:
	"""Night audit: a stay due on or before `business_date` that never checked in (F12).

	Its rooms go back, its nights are cancelled, and the no-show fee from its policy is charged and
	paid from the deposit. Returns False if the stay was handled already.
	"""
	stay = _lock_stay(stay_name)
	if stay.status not in ("Confirmed", "Due In") or getdate(stay.arrival_date) > getdate(business_date):
		return False
	from frappoint.vuna_hospitality.services import policies

	reason = _("Did not arrive on {0}").format(frappe.format(stay.arrival_date, "Date"))
	policies.post_fee(stay, policies.NO_SHOW, business_date=business_date)
	_release_occupancy(stay.room_occupancy, RELEASED)
	_cancel_room_assignment(stay)
	transition(stay, "No Show", reason=reason, event_type="No Show", ignore_permissions=True)
	_cancel_pending_nights(stay.name)
	from frappoint.vuna_hospitality.services.folio import close_idle_folios, refresh_stay_pending

	refresh_stay_pending(stay.name)
	_settle_deposit(stay.name, reason)
	close_idle_folios(stay.name, reason=reason)
	refresh_booking(stay.hotel_booking)
	return True


def reinstate(stay_name: str, reason: str) -> dict:
	"""Bring a cancelled or no-show stay back as Confirmed (design §11.2; plan F12).

	The rooms are taken again under the inventory lock, never assumed free: a sold-out night
	refuses the reinstatement. A no-show whose arrival has passed is reinstated from the business
	date. The booked prices come back; a fee not yet invoiced is reversed (an invoiced one needs a
	credit note).
	"""
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for reinstating stay {0}.").format(stay_name))
	stay = _lock_stay(stay_name)
	if stay.status not in ("Cancelled", "No Show"):
		raise InvalidTransitionError(
			_("Stay {0} is {1} and can't be reinstated.").format(stay.name, _(stay.status))
		)
	business_date = getdate(frappe.db.get_value("Hotel Property", stay.property, "business_date"))
	arrival = max(getdate(stay.arrival_date), business_date)
	departure = getdate(stay.departure_date)
	if arrival >= departure:
		frappe.throw(
			_("Stay {0} ended on {1}. Make a new booking instead.").format(
				stay.name, frappe.format(departure, "Date")
			),
			HoldRefusedError,
		)

	# Take the rooms first, under lock: this fails before anything is written if a night is full.
	inventory.acquire(stay.room_type, arrival, departure, kind=inventory.SOLD)
	occupancy = _new(
		OCCUPANCY,
		{
			"property": stay.property,
			"hotel_booking": stay.hotel_booking,
			"room_type": stay.room_type,
			"start_date": arrival,
			"end_date": departure,
			"allocation_state": HELD,
			"adults": stay.adults,
			"children": stay.children,
		},
	)
	transition(occupancy, CONFIRMED, event_type="Allocation Changed", ignore_permissions=True)
	_new(
		MEMBERSHIP,
		{
			"property": stay.property,
			"room_occupancy": occupancy.name,
			"stay_reservation": stay.name,
			"start_date": arrival,
			"end_date": departure,
			"reason": "Initial",
		},
	)
	_restore_nights(stay.name, arrival, departure)
	nights = frappe.get_all(
		RATE_NIGHT, filters={"stay_reservation": stay.name, "posting_state": "Pending"}, pluck="total"
	)
	total_minor = sum(to_minor(total, stay.currency) for total in nights)
	from_status = stay.status
	# The arrival moves to the business date for a late no-show; only this service may do that.
	stay.flags[SERVICE_FLAG] = True
	transition(
		stay,
		CONFIRMED,
		reason=reason,
		updates={
			"room_occupancy": occupancy.name,
			"arrival_date": arrival,
			"nights": len(nights),
			"total_amount": from_minor(total_minor, stay.currency),
			"average_rate": from_minor(total_minor // max(len(nights), 1), stay.currency),
			"cancelled_at": None,
			"cancelled_by": None,
			"cancellation_reason": None,
		},
		data={"from": from_status, "arrival": str(arrival), "departure": str(departure)},
		event_type="Reservation Reinstated",
		ignore_permissions=True,
	)
	_reopen_folios(stay.name, reason)
	from frappoint.vuna_hospitality.services.deposits import reopen
	from frappoint.vuna_hospitality.services.folio import refresh_stay_pending

	reopen(stay.name)
	refresh_stay_pending(stay.name)
	refresh_booking(stay.hotel_booking)
	return booking_summary(stay.hotel_booking)


def _restore_nights(stay_name: str, arrival, departure) -> None:
	table = frappe.qb.DocType(RATE_NIGHT)
	(
		frappe.qb.update(table)
		.set(table.posting_state, "Pending")
		.set(table.modified, now_datetime())
		.where(table.stay_reservation == stay_name)
		.where(table.posting_state == "Cancelled")
		.where(table.night_date >= arrival)
		.where(table.night_date < departure)
	).run()


def _reopen_folios(stay_name: str, reason: str) -> None:
	"""Reverse the fee not yet invoiced, and give the stay an open default folio again."""
	from frappoint.vuna_hospitality.services import folio, policies

	for line in policies.fee_lines(stay_name):
		if line.sales_invoice:
			continue
		row = folio.lock_folio(line.guest_folio)
		if row.status == folio.CLOSED:
			continue
		folio.reverse_transaction(line.name, _("Reinstated: {0}").format(reason))
	default = frappe.db.get_value(STAY, stay_name, "default_folio")
	row = default and frappe.db.get_value(folio.FOLIO, default, ["status", "sales_invoice"], as_dict=True)
	if row and row.status in folio.POSTABLE_STATUSES:
		return
	if row and row.status == folio.CLOSED and not row.sales_invoice:
		transition(
			frappe.get_doc(folio.FOLIO, default),
			folio.OPEN,
			reason=_("Reinstated: {0}").format(reason),
			updates={"closed_at": None, "closed_by": None},
			event_type="Folio Reopened",
			ignore_permissions=True,
		)
		return
	# The old default folio was invoiced (a forfeited deposit): the stay starts a new one.
	if default:
		frappe.db.set_value(folio.FOLIO, default, "is_default", 0, update_modified=False)
	frappe.db.set_value(STAY, stay_name, "default_folio", None, update_modified=False)
	folio.ensure_default_folio(stay_name)


def expire_hold(stay_name: str) -> bool:
	"""Release a hold that ran out. Returns False (and changes nothing) if it was already handled."""
	stay = _lock_stay(stay_name)
	if stay.status != HELD or not _hold_has_expired(stay):
		return False

	_release_occupancy(stay.room_occupancy, RELEASED)
	transition(
		stay,
		EXPIRED,
		updates={"hold_expires_at": None},
		data={"hold_expired_at": str(stay.hold_expires_at)},
		event_type="Hold Expired",
		ignore_permissions=True,
	)
	_cancel_pending_nights(stay.name)
	refresh_booking(stay.hotel_booking)
	return True


@hospitality_job
def expire_holds() -> int:
	"""Scheduled every minute: release every hold past its expiry, each in its own transaction."""
	names = frappe.get_all(
		STAY,
		filters={"status": HELD, "hold_expires_at": ["<=", now_datetime()]},
		pluck="name",
		order_by="hold_expires_at asc",
		limit=EXPIRY_BATCH,
	)
	expired = 0
	for name in names:
		try:
			expired += bool(inventory.run_with_inventory_retry(lambda name=name: expire_hold(name)))
			frappe.db.commit()  # nosemgrep
		except Exception:
			frappe.db.rollback()
			frappe.log_error(
				title=f"Hotel hold expiry failed: {name}", reference_doctype=STAY, reference_name=name
			)
	return expired


def _lock_row(doctype: str, name: str) -> None:
	try:
		found = frappe.db.get_value(doctype, name, "name", for_update=True)
	except frappe.QueryDeadlockError as error:
		raise inventory.InventoryConflictError(
			_("{0} {1} changed while this request was running. Please try again.").format(_(doctype), name)
		) from error
	if not found:
		frappe.throw(_("{0} {1} does not exist.").format(_(doctype), name), frappe.DoesNotExistError)


def _lock_stay(stay_name: str):
	_lock_row(STAY, stay_name)
	return frappe.get_doc(STAY, stay_name)


def _hold_has_expired(stay) -> bool:
	return bool(stay.hold_expires_at) and get_datetime(stay.hold_expires_at) <= now_datetime()


def _release_occupancy(occupancy_name: str, to_state: str) -> None:
	occupancy = frappe.get_doc(OCCUPANCY, occupancy_name)
	if occupancy.allocation_state not in ACTIVE_ALLOCATIONS:
		return
	kind = inventory.HELD if occupancy.allocation_state == HELD else inventory.SOLD
	inventory.release(occupancy.room_type, occupancy.start_date, occupancy.end_date, kind=kind)
	transition(
		occupancy,
		to_state,
		updates={"hold_expires_at": None},
		event_type="Allocation Changed",
		ignore_permissions=True,
	)


def _cancel_room_assignment(stay) -> None:
	"""A cancelled stay gives up the room it was assigned before arrival."""
	from frappoint.vuna_hospitality.services.front_desk import current_assignment

	assignment = current_assignment(stay.room_occupancy)
	if assignment and assignment.status == "Assigned":
		transition(assignment, "Cancelled", event_type="Room Unassigned", ignore_permissions=True)


def _cancel_pending_nights(stay_name: str) -> None:
	table = frappe.qb.DocType(RATE_NIGHT)
	(
		frappe.qb.update(table)
		.set(table.posting_state, "Cancelled")
		.set(table.modified, now_datetime())
		.where(table.stay_reservation == stay_name)
		.where(table.posting_state == "Pending")
	).run()


def _stays_of(booking: str, statuses) -> list[str]:
	return frappe.get_all(
		STAY,
		filters={"hotel_booking": booking, "status": ["in", list(statuses)]},
		pluck="name",
		order_by="creation asc",
	)


# --------------------------------------------------------------------------- booking status


def booking_status(stay_statuses: list[str]) -> str:
	"""A booking's status from its stays' statuses."""
	active = [status for status in stay_statuses if status not in INACTIVE_STAY_STATUSES]
	if not stay_statuses:
		return "Option"
	if not active:
		return "Cancelled"
	if all(status in FINISHED_STAY_STATUSES for status in active):
		return "Closed"
	if all(status == HELD for status in active):
		return "Option"
	return "Partly Cancelled" if len(active) < len(stay_statuses) else "Confirmed"


def refresh_booking(booking: str) -> None:
	"""Recompute the booking's status and totals from its stays."""
	_lock_row(BOOKING, booking)
	doc = frappe.get_doc(BOOKING, booking)
	stays = frappe.get_all(
		STAY, filters={"hotel_booking": booking}, fields=["status", "total_amount", "currency"]
	)
	active = [stay for stay in stays if stay.status not in INACTIVE_STAY_STATUSES]
	currency = next((stay.currency for stay in stays if stay.currency), doc.currency)
	totals = {
		"stay_count": len(active),
		"currency": currency,
		"total_amount": from_minor(sum(to_minor(stay.total_amount, currency) for stay in active), currency)
		if currency
		else 0,
	}
	status = booking_status([stay.status for stay in stays])
	if status != doc.status:
		transition(doc, status, updates=totals, event_type="Booking Status Changed", ignore_permissions=True)
	elif any(doc.get(field) != value for field, value in totals.items()):
		doc.update(totals)
		doc.save(ignore_permissions=True)


def booking_summary(booking: str) -> dict:
	"""The booking and its stays, as the booking desk shows them."""
	doc = frappe.get_doc(BOOKING, booking)
	stays = frappe.get_all(
		STAY,
		filters={"hotel_booking": booking},
		fields=[
			"name",
			"status",
			"room_type",
			"rate_plan",
			"arrival_date",
			"departure_date",
			"nights",
			"adults",
			"children",
			"lead_guest",
			"lead_guest_name",
			"total_amount",
			"average_rate",
			"currency",
			"hold_expires_at",
			"property",
			"cancellation_policy_snapshot",
		],
		order_by="creation asc",
	)
	from frappoint.vuna_hospitality.services import deposits, policies

	names = {
		**dict(
			frappe.get_all(
				"Room Type",
				filters={"name": ["in", [s.room_type for s in stays] or [""]]},
				fields=["name", "room_type_name"],
				as_list=True,
			)
		),
		**dict(
			frappe.get_all(
				"Rate Plan",
				filters={"name": ["in", [s.rate_plan for s in stays] or [""]]},
				fields=["name", "rate_plan_name"],
				as_list=True,
			)
		),
	}
	now = now_datetime()
	for stay in stays:
		stay["hold_seconds_left"] = (
			max(0, int((get_datetime(stay.hold_expires_at) - now).total_seconds()))
			if stay.status == HELD and stay.hold_expires_at
			else None
		)
		stay["room_type_name"] = names.get(stay.room_type)
		stay["rate_plan_name"] = names.get(stay.rate_plan)
		stay["can_confirm"] = stay.status == HELD
		stay["can_cancel"] = stay.status in CANCELLABLE_STAY_STATUSES
		stay["can_reinstate"] = stay.status in ("Cancelled", "No Show")
		# F12: what cancelling now would charge, and the deposit.
		quote = (
			policies.fee_quote(stay, policies.CANCELLATION)
			if stay.status in CANCELLABLE_STAY_STATUSES and stay.status != HELD
			else None
		)
		stay["cancellation_fee"] = quote.amount if quote else 0
		stay["free_cancellation_until"] = quote.free_until if quote else None
		stay["cancellation_policy_name"] = quote.policy_name if quote else None
		stay["deposit"] = deposits.deposit_details(stay.name)
		del stay["cancellation_policy_snapshot"]
	return {
		"name": doc.name,
		"property": doc.property,
		"status": doc.status,
		"booking_source": doc.booking_source,
		"booker_guest_profile": doc.booker_guest_profile,
		"booker_name": doc.booker_name,
		"booker_customer": doc.booker_customer,
		"sales_partner": doc.sales_partner,
		"external_reference": doc.external_reference,
		"currency": doc.currency,
		"total_amount": doc.total_amount,
		"stay_count": doc.stay_count,
		"stays": stays,
		"can_waive_fees": bool(set(FOLIO_MANAGER_ROLES) & set(frappe.get_roles())),
		"can_reinstate": bool(set(RESERVATION_MANAGER_ROLES) & set(frappe.get_roles())),
	}


# --------------------------------------------------------------------------- inventory demand


def occupancy_demand(room_types: list[str], nights: list[date]) -> dict:
	"""Inventory demand source: held and confirmed Room Occupancies, counted per room type and night."""
	if not room_types or not nights:
		return {}
	wanted = set(nights)
	demand: dict = defaultdict(lambda: {"held": 0, "sold": 0})
	for row in frappe.get_all(
		OCCUPANCY,
		filters={
			"room_type": ["in", list(room_types)],
			"allocation_state": ["in", list(ACTIVE_ALLOCATIONS)],
			"occupancy_type": "Overnight",
			"start_date": ["<=", max(nights)],
			"end_date": [">", min(nights)],
		},
		fields=["room_type", "allocation_state", "start_date", "end_date"],
	):
		field = "held" if row.allocation_state == HELD else "sold"
		for night in inventory.nights_between(row.start_date, row.end_date):
			if night in wanted:
				demand[(row.room_type, night)][field] += 1
	return dict(demand)


# --------------------------------------------------------------------------- setup


def booking_sources() -> list[str]:
	"""The UTM Sources the booking desk offers: Hospitality Settings' list, or every UTM Source."""
	chosen = frappe.get_all(
		"Hospitality Booking Source",
		filters={"parenttype": SETTINGS, "parent": SETTINGS},
		pluck="utm_source",
		order_by="idx asc",
	)
	return chosen or frappe.get_all(UTM_SOURCE, pluck="name", order_by="name asc")


@hospitality_job
def install_hospitality_defaults() -> None:
	"""Create what a site needs to start taking bookings. Runs after migrate and when hospitality is
	switched on; safe to run again.

	- the default booking sources as UTM Sources, offered on the booking desk;
	- the default room move reasons;
	- read access to Sales Partner for hospitality roles, so they can pick a booking's partner;
	- select access to Account for the roles that take payments (F10), because ERPNext's Payment
	  Entry checks that its user may select the receivable and cash accounts. Select doesn't let
	  them read balances;
	- read access to Item and Sales Invoice for the roles that settle folios (F11), because
	  ERPNext checks both while it builds and submits the settlement invoice.
	"""
	from frappoint.vuna_hospitality.services.front_desk import install_default_move_reasons

	install_default_move_reasons()
	_install_booking_sources()
	_grant_sales_partner_access()
	_grant_account_select_access()
	_grant_settlement_access()


def _install_booking_sources() -> None:
	for source in DEFAULT_BOOKING_SOURCES:
		if not frappe.db.exists(UTM_SOURCE, source):
			frappe.get_doc({"doctype": UTM_SOURCE, "name": source}).insert(ignore_permissions=True)
	settings = frappe.get_single(SETTINGS)
	if settings.meta.has_field("booking_sources") and not settings.booking_sources:
		for source in DEFAULT_BOOKING_SOURCES:
			settings.append("booking_sources", {"utm_source": source})
		settings.flags.ignore_permissions = True
		settings.save()


def _grant_sales_partner_access() -> None:
	from frappe.permissions import add_permission

	from frappoint.vuna_hospitality.constants import HOSPITALITY_ROLES

	for role in HOSPITALITY_ROLES:
		if not frappe.db.exists("Role", role):
			continue
		if not frappe.db.exists("Custom DocPerm", {"parent": "Sales Partner", "role": role, "permlevel": 0}):
			add_permission("Sales Partner", role, 0, "select")


def _grant_account_select_access() -> None:
	from frappe.permissions import add_permission

	from frappoint.vuna_hospitality.constants import CASHIER_ROLES

	granted = False
	for role in CASHIER_ROLES:
		if role == "System Manager" or not frappe.db.exists("Role", role):
			continue
		if not frappe.db.exists("Custom DocPerm", {"parent": "Account", "role": role, "permlevel": 0}):
			add_permission("Account", role, 0, "select")
			# A new rule also gets read by default; these roles only pick accounts.
			frappe.db.set_value(
				"Custom DocPerm", {"parent": "Account", "role": role, "permlevel": 0}, "read", 0
			)
			granted = True
	if granted:
		frappe.clear_cache(doctype="Account")


def _grant_settlement_access() -> None:
	"""Let the roles that settle folios read Items and Sales Invoices (F11).

	ERPNext checks both while it builds and submits the settlement invoice, and the desk shows and
	prints the invoice afterwards. Creating and submitting it stays a folio action: these roles get
	no create or submit rights on Sales Invoice."""
	from frappe.permissions import add_permission

	from frappoint.vuna_hospitality.constants import FOLIO_ACCOUNTING_ROLES, SETTLEMENT_ROLES

	granted = False
	for role in {*SETTLEMENT_ROLES, *FOLIO_ACCOUNTING_ROLES}:
		if role == "System Manager" or not frappe.db.exists("Role", role):
			continue
		for doctype in ("Item", "Sales Invoice"):
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
				add_permission(doctype, role, 0, "read")
				granted = True
	if granted:
		frappe.clear_cache(doctype="Item")
		frappe.clear_cache(doctype="Sales Invoice")
