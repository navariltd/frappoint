"""Booking, hold, and confirm (design §11, §28.4, §30.8-30.12; feature F5).

A Hotel Booking holds one or more Stay Reservations. Each stay puts demand on inventory through a
Room Occupancy, linked to the stay by an Occupancy Membership, and keeps its price as one Stay Rate
Night per night, copied from the quote.

Commands (every one runs in the caller's transaction and is safe to retry in a new one):

- `hold()`: quote, take the rooms as *held* under lock, and create the records, all at once.
- `confirm()`: turn the held rooms into *sold* rooms.
- `cancel()`: give the rooms back. Cancellation fees come with F12.
- `expire_hold()`: give back the rooms of a hold that ran out; `expire_holds()` is the job.

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
DEFAULT_BOOKING_SOURCES = ("Walk-in", "Phone", "Email", "Website", "Travel Agent", "Corporate")
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

	policies = _row("Rate Plan", stay.rate_plan, ["cancellation_policy", "deposit_policy"])
	return frappe._dict(
		stay=stay,
		quote=stay_quote,
		room_type=stay_quote.room_type,
		arrival=arrival,
		departure=departure,
		cancellation_policy=policies.cancellation_policy,
		deposit_policy=policies.deposit_policy,
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
		"travel_agent",
		"external_reference",
		"guarantee_type",
		"notes",
	)
	values = {field: details.get(field) for field in allowed if details.get(field)}
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
			"cancellation_policy": p.cancellation_policy,
			"cancellation_policy_snapshot": _policy_snapshot(p.cancellation_policy),
			"deposit_policy": p.deposit_policy,
			"deposit_policy_snapshot": _policy_snapshot(p.deposit_policy),
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
				"room_rate": amount,
				"total": amount,
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
	refresh_booking(stay.hotel_booking)
	return booking_summary(stay.hotel_booking)


def confirm_booking(booking: str) -> dict:
	"""Confirm every held stay on the booking."""
	for name in _stays_of(booking, (HELD,)):
		confirm(name)
	return booking_summary(booking)


def cancel(stay_name: str, reason: str) -> dict:
	"""Cancel a held or confirmed stay and give its rooms back. Cancelling twice changes nothing."""
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
	refresh_booking(stay.hotel_booking)
	return booking_summary(stay.hotel_booking)


def cancel_booking(booking: str, reason: str) -> dict:
	"""Cancel every held or confirmed stay on the booking."""
	for name in _stays_of(booking, CANCELLABLE_STAY_STATUSES):
		cancel(name, reason)
	return booking_summary(booking)


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
		],
		order_by="creation asc",
	)
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
	return {
		"name": doc.name,
		"property": doc.property,
		"status": doc.status,
		"booking_source": doc.booking_source,
		"booker_guest_profile": doc.booker_guest_profile,
		"booker_name": doc.booker_name,
		"booker_customer": doc.booker_customer,
		"external_reference": doc.external_reference,
		"currency": doc.currency,
		"total_amount": doc.total_amount,
		"stay_count": doc.stay_count,
		"stays": stays,
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


@hospitality_job
def install_default_booking_sources() -> None:
	"""Create the usual booking sources and room move reasons once, so a site can start straight away.

	Runs after migrate and when hospitality is switched on.
	"""
	from frappoint.vuna_hospitality.services.front_desk import install_default_move_reasons

	install_default_move_reasons()
	if not frappe.db.table_exists("Hotel Booking Source"):
		return
	for source in DEFAULT_BOOKING_SOURCES:
		if not frappe.db.exists("Hotel Booking Source", source):
			frappe.get_doc({"doctype": "Hotel Booking Source", "source_name": source}).insert(
				ignore_permissions=True
			)
