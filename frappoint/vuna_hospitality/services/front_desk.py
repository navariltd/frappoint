"""Stay guests, room assignment, check-in and check-out (design §12, §28.4, §30.13-30.14; feature F6).

- **Stay Guest**: every person in a stay. The lead guest is the Primary; companions are added,
  registered, and checked in one by one. The Room Occupancy's adults and children follow them.
- **Room Assignment**: a dated segment of a stay in one physical room. Assigning locks the Hotel
  Room row and refuses the room if another stay holds it at overlapping *times*, including the
  property's turnover time, so early check-in and late check-out are respected. A move ends one
  segment and starts the next, so the stay's history keeps every room.
- **Check-in** needs a ready room (housekeeping Inspected or Clean, until F17), every adult
  registered, and a satisfied guarantee (F12). **Check-out** first posts the nights the guest used
  that night audit hasn't (F8), then needs every open folio at zero (F7), unless a Front Desk
  Manager overrides it with a reason. Leaving before the booked departure gives the remaining
  nights back to inventory. Folios with nothing to invoice close at check-out.

Lock order follows reservations.py: the stay first, then rooms (by name), then inventory rows,
then the booking.
"""

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, getdate, now_datetime

from frappoint.vuna_hospitality.constants import FOLIO_MANAGER_ROLES
from frappoint.vuna_hospitality.services import folio, inventory, night_audit, reservations
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.guests import assert_registrable
from frappoint.vuna_hospitality.services.money import from_minor, to_minor
from frappoint.vuna_hospitality.services.reservations import (
	MEMBERSHIP,
	OCCUPANCY,
	RATE_NIGHT,
	STAY,
	_lock_row,
	_lock_stay,
	_new,
	_row,
	refresh_booking,
)
from frappoint.vuna_hospitality.services.rooms import mark_room
from frappoint.vuna_hospitality.services.status_commands import transition

STAY_GUEST = "Stay Guest"
STAY_GUEST_PROFILE = "Guest Profile"
ASSIGNMENT = "Room Assignment"
HOTEL_ROOM = "Hotel Room"

PRIMARY, COMPANION = "Primary", "Companion"
ADULT = "Adult"
ACTIVE_GUEST_STATUSES = ("Expected", "Registered", "Checked In")
ACTIVE_ASSIGNMENTS = ("Assigned", "Occupied")
READY_CONDITIONS = ("Inspected", "Clean")
PRE_ARRIVAL_STATUSES = ("Confirmed", "Due In")
GUEST_EDITABLE_STATUSES = ("Held", "Confirmed", "Due In", "In House", "Due Out")
IN_HOUSE_STATUSES = ("In House", "Due Out")
DEFAULT_MOVE_REASONS = ("Guest Request", "Maintenance", "Upgrade", "Noise", "Other")


class RoomUnavailableError(frappe.ValidationError):
	"""The room can't be given to this stay: wrong type, closed, or taken at overlapping times."""


class CheckInRefusedError(frappe.ValidationError):
	"""Something check-in needs is missing: a ready room, a registered guest, or the arrival date."""


# --------------------------------------------------------------------------- stay guests


def add_primary_guest(stay) -> str:
	"""Record the lead guest as the stay's Primary guest. Called when a stay is created."""
	return _insert_stay_guest(stay, stay.lead_guest, PRIMARY, ADULT)


def add_stay_guest(
	stay_name: str,
	guest_profile: str,
	role: str = COMPANION,
	age_category: str = ADULT,
	guardian: str | None = None,
) -> str:
	"""Add a person to the stay. Children and infants get a guardian (default: the primary guest)."""
	stay = _lock_stay(stay_name)
	if stay.status not in GUEST_EDITABLE_STATUSES:
		frappe.throw(_("Guests can't be added to a stay that is {0}.").format(_(stay.status)))
	if role == PRIMARY:
		frappe.throw(_("Add the guest as a companion, then make them the primary guest."))
	reservations._check_lead_guest(guest_profile)
	if frappe.db.exists(
		STAY_GUEST,
		{
			"stay_reservation": stay.name,
			"guest_profile": guest_profile,
			"status": ["in", ACTIVE_GUEST_STATUSES],
		},
	):
		frappe.throw(_("This guest is already on stay {0}.").format(stay.name))

	if age_category != ADULT and not guardian:
		guardian = stay.lead_guest
	_check_capacity(stay, extra_adults=int(age_category == ADULT), extra_children=int(age_category != ADULT))
	name = _insert_stay_guest(stay, guest_profile, COMPANION, age_category, guardian)
	_sync_occupancy_counts(stay)
	log_event(
		STAY,
		stay.name,
		"Stay Guest Added",
		data={"stay_guest": name, "guest_profile": guest_profile, "age_category": age_category},
	)
	return name


def remove_stay_guest(stay_guest: str, reason: str) -> None:
	"""Take a guest who never arrived off the stay. The primary guest can't be removed."""
	guest = frappe.get_doc(STAY_GUEST, stay_guest)
	stay = _lock_stay(guest.stay_reservation)
	guest.reload()
	if guest.role == PRIMARY:
		frappe.throw(_("Make another guest the primary guest before removing {0}.").format(guest.guest_name))
	if guest.status == "Checked In":
		frappe.throw(_("{0} is checked in; check the stay out instead.").format(guest.guest_name))
	transition(guest, "Removed", reason=reason, updates={"removed_reason": reason}, ignore_permissions=True)
	_sync_occupancy_counts(stay)


def set_primary_guest(stay_guest: str, reason: str | None = None) -> None:
	"""Make this guest the stay's primary guest; the previous primary becomes a companion."""
	guest = frappe.get_doc(STAY_GUEST, stay_guest)
	stay = _lock_stay(guest.stay_reservation)
	guest.reload()
	if guest.role == PRIMARY:
		return
	if guest.status not in ACTIVE_GUEST_STATUSES or guest.age_category != ADULT:
		frappe.throw(_("Only an adult guest on the stay can be its primary guest."))
	reservations._check_lead_guest(guest.guest_profile)

	previous = frappe.get_all(
		STAY_GUEST, filters={"stay_reservation": stay.name, "role": PRIMARY}, pluck="name"
	)
	for name in previous:
		frappe.db.set_value(STAY_GUEST, name, "role", COMPANION)
	guest.db_set("role", PRIMARY)

	stay.lead_guest = guest.guest_profile
	stay.flags[reservations.SERVICE_FLAG] = True
	stay.save(ignore_permissions=True)
	log_event(
		STAY,
		stay.name,
		"Primary Guest Changed",
		reason=reason,
		data={"from": previous, "to": guest.name, "guest_profile": guest.guest_profile},
	)


def register_guest(stay_guest: str) -> None:
	"""Complete a guest's registration: a real (not provisional) profile, captured as registered."""
	guest = frappe.get_doc(STAY_GUEST, stay_guest)
	if guest.status not in ("Expected", "Registered"):
		frappe.throw(_("{0} is {1} and can't be registered.").format(guest.guest_name, _(guest.status)))
	assert_registrable(guest.guest_profile)
	profile = _row(
		STAY_GUEST_PROFILE, guest.guest_profile, ["full_name", "email", "mobile_no", "nationality"]
	)
	updates = {
		"registration_complete": 1,
		"registered_at": now_datetime(),
		"name_snapshot": profile.full_name,
		"contact_snapshot": frappe.as_json(
			{"email": profile.email, "mobile_no": profile.mobile_no, "nationality": profile.nationality}
		),
	}
	if guest.status == "Registered":
		guest.update(updates)
		guest.save(ignore_permissions=True)
	else:
		transition(
			guest, "Registered", updates=updates, event_type="Guest Registered", ignore_permissions=True
		)


def _insert_stay_guest(stay, guest_profile, role, age_category, guardian=None) -> str:
	start, end = stay_window(stay)
	return _new(
		STAY_GUEST,
		{
			"property": stay.property,
			"stay_reservation": stay.name,
			"guest_profile": guest_profile,
			"role": role,
			"age_category": age_category,
			"guardian": guardian,
			"status": "Expected",
			"expected_arrival": start,
			"expected_departure": end,
		},
	).name


def active_guests(stay_name: str) -> list:
	return frappe.get_all(
		STAY_GUEST,
		filters={"stay_reservation": stay_name, "status": ["in", ACTIVE_GUEST_STATUSES]},
		fields=[
			"name",
			"guest_profile",
			"guest_name",
			"role",
			"age_category",
			"status",
			"registration_complete",
		],
		order_by="creation asc",
	)


def _check_capacity(stay, extra_adults: int = 0, extra_children: int = 0) -> None:
	room_type = _row(
		"Room Type", stay.room_type, ["room_type_name", "max_adults", "max_children", "max_occupancy"]
	)
	guests = active_guests(stay.name)
	adults = sum(g.age_category == ADULT for g in guests) + extra_adults
	children = len(guests) - sum(g.age_category == ADULT for g in guests) + extra_children
	if (
		adults > cint(room_type.max_adults)
		or children > cint(room_type.max_children)
		or adults + children > cint(room_type.max_occupancy)
	):
		frappe.throw(
			_("A {0} sleeps at most {1} adults, {2} children and {3} people in all.").format(
				room_type.room_type_name,
				room_type.max_adults,
				room_type.max_children,
				room_type.max_occupancy,
			)
		)


def _sync_occupancy_counts(stay) -> None:
	"""The Room Occupancy's adults and children are derived from the stay's active guests."""
	guests = active_guests(stay.name)
	adults = sum(g.age_category == ADULT for g in guests)
	frappe.db.set_value(OCCUPANCY, stay.room_occupancy, {"adults": adults, "children": len(guests) - adults})


# --------------------------------------------------------------------------- room assignment


def stay_window(stay, start_date=None, end_date=None) -> tuple[datetime, datetime]:
	"""The datetimes a stay holds its room: check-in time on arrival to check-out time on departure."""
	times = _row("Hotel Property", stay.property, ["check_in_time", "check_out_time"])
	start = get_datetime(f"{getdate(start_date or stay.arrival_date)} {times.check_in_time or '14:00:00'}")
	end = get_datetime(f"{getdate(end_date or stay.departure_date)} {times.check_out_time or '10:00:00'}")
	return start, end


def find_conflict(
	room: str, start: datetime, end: datetime, turnover_minutes: int, exclude_occupancy: str | None
):
	"""An active assignment of `room` that overlaps [start, end), allowing turnover time between stays."""
	gap = timedelta(minutes=cint(turnover_minutes))
	filters = {
		"hotel_room": room,
		"status": ["in", ACTIVE_ASSIGNMENTS],
		"start_datetime": ["<", end + gap],
		"end_datetime": [">", start - gap],
	}
	if exclude_occupancy:
		filters["room_occupancy"] = ["!=", exclude_occupancy]
	return frappe.db.get_value(ASSIGNMENT, filters, "name")


def room_closed(room: str, start_date, end_date) -> str | None:
	"""The out-of-order or out-of-service state covering any night in [start_date, end_date)."""
	return frappe.db.get_value(
		"Room State Period",
		{
			"room": room,
			"docstatus": 1,
			"from_date": ["<", getdate(end_date)],
			"to_date": [">", getdate(start_date)],
		},
		"state",
	)


def current_assignment(occupancy: str):
	"""The occupancy's active assignment, or None."""
	name = frappe.db.get_value(
		ASSIGNMENT, {"room_occupancy": occupancy, "status": ["in", ACTIVE_ASSIGNMENTS]}, "name"
	)
	return frappe.get_doc(ASSIGNMENT, name) if name else None


def _check_room(stay, room: str, start: datetime, end: datetime, start_date, end_date) -> frappe._dict:
	info = _row(
		HOTEL_ROOM,
		room,
		["name", "property", "room_number", "room_type", "is_active", "housekeeping_condition"],
	)
	if not info:
		frappe.throw(_("Room {0} does not exist.").format(room), RoomUnavailableError)
	if info.property != stay.property:
		frappe.throw(
			_("Room {0} belongs to another property.").format(info.room_number), RoomUnavailableError
		)
	if not info.is_active:
		frappe.throw(_("Room {0} is inactive.").format(info.room_number), RoomUnavailableError)
	if info.room_type != stay.room_type:
		frappe.throw(
			_("Room {0} is not a {1}. Upgrades come in a later release.").format(
				info.room_number, frappe.db.get_value("Room Type", stay.room_type, "room_type_name")
			),
			RoomUnavailableError,
		)
	closed = room_closed(room, start_date, end_date)
	if closed:
		frappe.throw(
			_("Room {0} is {1} during this stay.").format(info.room_number, _(closed)), RoomUnavailableError
		)
	turnover = frappe.db.get_value("Hotel Property", stay.property, "turnover_minutes")
	conflict = find_conflict(room, start, end, turnover, stay.room_occupancy)
	if conflict:
		other = frappe.db.get_value(ASSIGNMENT, conflict, "stay_reservation")
		frappe.throw(
			_("Room {0} is taken by stay {1} at overlapping times.").format(info.room_number, other),
			RoomUnavailableError,
		)
	return info


def get_assignable_rooms(stay_name: str) -> list[dict]:
	"""Rooms of the stay's type, with whether each is free for the stay and ready for check-in."""
	stay = frappe.get_doc(STAY, stay_name)
	start, end = stay_window(stay)
	turnover = frappe.db.get_value("Hotel Property", stay.property, "turnover_minutes")
	current = current_assignment(stay.room_occupancy)
	rooms = frappe.get_all(
		HOTEL_ROOM,
		filters={"room_type": stay.room_type, "is_active": 1},
		fields=["name", "room_number", "floor", "housekeeping_condition", "occupancy_status"],
		order_by="room_number asc",
	)
	for room in rooms:
		conflict = find_conflict(room.name, start, end, turnover, stay.room_occupancy)
		closed = room_closed(room.name, stay.arrival_date, stay.departure_date)
		room["is_current"] = bool(current and current.hotel_room == room.name)
		room["available"] = not conflict and not closed
		room["unavailable_reason"] = _(closed) if closed else (_("Taken") if conflict else None)
		room["ready"] = room.housekeeping_condition in READY_CONDITIONS
	return rooms


def assign_room(stay_name: str, room: str, lock: bool = False, notes: str | None = None) -> str:
	"""Give the stay a physical room before arrival (or change it). Returns the assignment name."""
	stay = _lock_stay(stay_name)
	if stay.status not in PRE_ARRIVAL_STATUSES:
		frappe.throw(
			_("Rooms are assigned to confirmed stays before arrival. Stay {0} is {1}.").format(
				stay.name, _(stay.status)
			)
		)
	current = current_assignment(stay.room_occupancy)
	if current and current.hotel_room == room:
		if cint(lock) and not current.do_not_move:
			set_room_lock(stay.name, True)
		return current.name
	if current and current.do_not_move:
		frappe.throw(
			_("Room {0} is locked to this stay (Do Not Move). Unlock it first.").format(current.room_number)
		)

	_lock_row(HOTEL_ROOM, room)
	start, end = stay_window(stay)
	info = _check_room(stay, room, start, end, stay.arrival_date, stay.departure_date)
	if current:
		transition(current, "Cancelled", event_type="Room Unassigned", ignore_permissions=True)
	assignment = _new(
		ASSIGNMENT,
		{
			"property": stay.property,
			"room_occupancy": stay.room_occupancy,
			"stay_reservation": stay.name,
			"hotel_room": room,
			"status": "Assigned",
			"do_not_move": cint(lock),
			"start_date": stay.arrival_date,
			"end_date": stay.departure_date,
			"start_datetime": start,
			"end_datetime": end,
			"notes": notes,
		},
	)
	log_event(
		STAY,
		stay.name,
		"Room Assigned",
		data={
			"assignment": assignment.name,
			"room": info.room_number,
			"replaced": current.name if current else None,
		},
	)
	return assignment.name


def unassign_room(stay_name: str, reason: str | None = None) -> None:
	"""Take the room off a stay that hasn't arrived."""
	stay = _lock_stay(stay_name)
	current = current_assignment(stay.room_occupancy)
	if not current:
		return
	if current.status != "Assigned":
		frappe.throw(_("The guest is in room {0}; move or check out instead.").format(current.room_number))
	if current.do_not_move:
		frappe.throw(
			_("Room {0} is locked to this stay (Do Not Move). Unlock it first.").format(current.room_number)
		)
	transition(current, "Cancelled", reason=reason, event_type="Room Unassigned", ignore_permissions=True)


def set_room_lock(stay_name: str, locked: bool, reason: str | None = None) -> None:
	"""Set or clear "Do Not Move" on the stay's room."""
	stay = _lock_stay(stay_name)
	current = current_assignment(stay.room_occupancy)
	if not current:
		frappe.throw(_("Assign a room before locking it."))
	if bool(current.do_not_move) == bool(cint(locked)):
		return
	current.db_set("do_not_move", cint(locked))
	log_event(
		ASSIGNMENT,
		current.name,
		"Room Locked" if cint(locked) else "Room Unlocked",
		reason=reason,
		property_name=stay.property,
	)


def move_room(stay_name: str, new_room: str, move_reason: str, notes: str | None = None) -> str:
	"""Move an in-house stay to another room now. The old segment ends; a new one starts."""
	stay = _lock_stay(stay_name)
	if stay.status not in IN_HOUSE_STATUSES:
		frappe.throw(_("Only in-house stays are moved. Before arrival, assign another room instead."))
	if not move_reason:
		frappe.throw(_("Choose a move reason."))
	current = current_assignment(stay.room_occupancy)
	if not current or current.status != "Occupied":
		frappe.throw(_("Stay {0} has no occupied room to move from.").format(stay.name))
	if current.hotel_room == new_room:
		frappe.throw(_("The guest is already in room {0}.").format(current.room_number))
	if current.do_not_move:
		frappe.throw(
			_("Room {0} is locked to this stay (Do Not Move). Unlock it first.").format(current.room_number)
		)

	for room in sorted((current.hotel_room, new_room)):
		_lock_row(HOTEL_ROOM, room)
	now = now_datetime()
	business_date = _business_date(stay.property)
	# The stay keeps its planned check-out; read it before the current segment is closed at `now`.
	planned_end = get_datetime(current.end_datetime)
	info = _check_room(stay, new_room, now, planned_end, business_date, stay.departure_date)
	if info.housekeeping_condition not in READY_CONDITIONS:
		frappe.throw(
			_("Room {0} is {1}, not ready for a guest.").format(
				info.room_number, _(info.housekeeping_condition)
			),
			RoomUnavailableError,
		)

	transition(
		current,
		"Released",
		updates={"end_datetime": now, "end_date": business_date},
		event_type="Room Released",
		ignore_permissions=True,
	)
	new = _new(
		ASSIGNMENT,
		{
			"property": stay.property,
			"room_occupancy": stay.room_occupancy,
			"stay_reservation": stay.name,
			"hotel_room": new_room,
			"status": "Occupied",
			"start_date": business_date,
			"end_date": stay.departure_date,
			"start_datetime": now,
			"end_datetime": planned_end,
			"previous_assignment": current.name,
			"move_reason": move_reason,
			"notes": notes,
		},
	)
	mark_room(
		current.hotel_room,
		occupancy_status="Vacant",
		housekeeping_condition="Dirty",
		reason=_("Guest moved out"),
	)
	mark_room(new_room, occupancy_status="Occupied", reason=_("Guest moved in"))
	log_event(
		STAY,
		stay.name,
		"Room Moved",
		reason=move_reason,
		data={"from": current.room_number, "to": info.room_number, "assignment": new.name},
	)
	return new.name


# --------------------------------------------------------------------------- check-in / check-out


def check_in(stay_name: str, room: str | None = None) -> None:
	"""Check the stay in: the room becomes occupied and every registered guest is checked in."""
	stay = _lock_stay(stay_name)
	if stay.status not in PRE_ARRIVAL_STATUSES:
		raise CheckInRefusedError(
			_("Stay {0} is {1} and can't be checked in.").format(stay.name, _(stay.status))
		)
	business_date = _business_date(stay.property)
	if getdate(stay.arrival_date) > business_date:
		raise CheckInRefusedError(
			_("Stay {0} arrives on {1}. Check-in opens on the arrival date.").format(
				stay.name, frappe.format(stay.arrival_date, "Date")
			)
		)
	if getdate(stay.departure_date) <= business_date:
		raise CheckInRefusedError(_("Stay {0} has already passed its departure date.").format(stay.name))

	if room:
		assign_room(stay.name, room)
	assignment = current_assignment(stay.room_occupancy)
	if not assignment:
		raise CheckInRefusedError(_("Assign a room before checking in."))
	_lock_row(HOTEL_ROOM, assignment.hotel_room)
	condition = frappe.db.get_value(HOTEL_ROOM, assignment.hotel_room, "housekeeping_condition")
	if condition not in READY_CONDITIONS:
		raise CheckInRefusedError(
			_("Room {0} is {1}. It must be Clean or Inspected before check-in.").format(
				assignment.room_number, _(condition)
			)
		)

	guests = active_guests(stay.name)
	unregistered = [g.guest_name for g in guests if g.age_category == ADULT and not g.registration_complete]
	if unregistered:
		raise CheckInRefusedError(
			_("Register every adult before check-in: {0}.").format(", ".join(unregistered))
		)
	assert_guarantee_satisfied(stay)
	# Stays confirmed before folios existed get theirs here, so every in-house stay has one.
	folio.ensure_default_folio(stay.name)

	now = now_datetime()
	for guest in guests:
		transition(
			(STAY_GUEST, guest.name),
			"Checked In",
			updates={"actual_check_in": now},
			event_type="Guest Checked In",
			ignore_permissions=True,
		)
	transition(
		assignment,
		"Occupied",
		updates={"start_datetime": min(now, get_datetime(assignment.start_datetime))},
		event_type="Room Occupied",
		ignore_permissions=True,
	)
	transition(
		stay,
		"In House",
		event_type="Checked In",
		data={"room": assignment.room_number},
		ignore_permissions=True,
	)
	mark_room(
		assignment.hotel_room, occupancy_status="Occupied", reason=_("Checked in: {0}").format(stay.name)
	)
	refresh_booking(stay.hotel_booking)


def check_in_guest(stay_guest: str) -> None:
	"""Check in a companion who arrives after the stay was checked in."""
	guest = frappe.get_doc(STAY_GUEST, stay_guest)
	stay = _lock_stay(guest.stay_reservation)
	if stay.status not in IN_HOUSE_STATUSES:
		frappe.throw(_("Check the stay in first."))
	guest.reload()
	if guest.age_category == ADULT and not guest.registration_complete:
		frappe.throw(_("Register {0} before checking them in.").format(guest.guest_name))
	transition(
		guest,
		"Checked In",
		updates={"actual_check_in": now_datetime()},
		event_type="Guest Checked In",
		ignore_permissions=True,
	)


def check_out(stay_name: str, override_reason: str | None = None) -> None:
	"""Check the stay out. Leaving before the booked departure gives the remaining nights back.

	Every open folio must be at zero. `override_reason` lets a Front Desk Manager check the guest
	out anyway; the folios then stay open for settlement.
	"""
	stay = _lock_stay(stay_name)
	if stay.status not in IN_HOUSE_STATUSES:
		frappe.throw(_("Stay {0} is {1} and can't be checked out.").format(stay.name, _(stay.status)))

	now = now_datetime()
	business_date = _business_date(stay.property)
	# The guest is charged at least the first night.
	leaving_on = max(business_date, add_days(stay.arrival_date, 1))
	# Nights the guest used that night audit hasn't posted yet (a same-day departure) are charged
	# now, with night audit's posting keys, so they are settled before the guest leaves.
	night_audit.post_due_nights(stay.name, leaving_on, business_date)
	assert_ready_to_check_out(stay, override_reason)

	early = getdate(leaving_on) < getdate(stay.departure_date)
	if early:
		_shorten_stay(stay, getdate(leaving_on))

	assignment = current_assignment(stay.room_occupancy)
	if assignment:
		transition(
			assignment,
			"Released",
			updates={"end_datetime": now, "end_date": leaving_on},
			event_type="Room Released",
			ignore_permissions=True,
		)
		mark_room(
			assignment.hotel_room,
			occupancy_status="Vacant",
			housekeeping_condition="Dirty",
			reason=_("Checked out: {0}").format(stay.name),
		)
	for guest in active_guests(stay.name):
		if guest.status == "Checked In":
			transition(
				(STAY_GUEST, guest.name),
				"Checked Out",
				updates={"actual_check_out": now},
				ignore_permissions=True,
			)
		else:
			transition((STAY_GUEST, guest.name), "Did Not Stay", ignore_permissions=True)
	transition(
		stay,
		"Checked Out",
		event_type="Checked Out",
		data={"early_departure": early},
		ignore_permissions=True,
	)
	folio.close_idle_folios(stay.name, reason=_("Checked out with nothing to invoice"))
	refresh_booking(stay.hotel_booking)


def _shorten_stay(stay, new_departure) -> None:
	"""Early departure: release the remaining nights and stop pricing them. The fee comes with F12."""
	occupancy = frappe.get_doc(OCCUPANCY, stay.room_occupancy)
	inventory.release(occupancy.room_type, new_departure, stay.departure_date, kind=inventory.SOLD)
	table = frappe.qb.DocType(RATE_NIGHT)
	(
		frappe.qb.update(table)
		.set(table.posting_state, "Cancelled")
		.set(table.override_reason, _("Early departure"))
		.where(table.stay_reservation == stay.name)
		.where(table.night_date >= new_departure)
		.where(table.posting_state == "Pending")
	).run()
	kept = frappe.get_all(
		RATE_NIGHT,
		filters={"stay_reservation": stay.name, "posting_state": ["!=", "Cancelled"]},
		pluck="total",
	)
	total_minor = sum(to_minor(amount, stay.currency) for amount in kept)
	nights = len(inventory.nights_between(stay.arrival_date, new_departure))
	booked_departure = stay.departure_date
	frappe.db.set_value(OCCUPANCY, occupancy.name, "end_date", new_departure)
	frappe.db.set_value(
		MEMBERSHIP,
		{"room_occupancy": occupancy.name, "stay_reservation": stay.name},
		"end_date",
		new_departure,
	)
	stay.update(
		{
			"departure_date": new_departure,
			"nights": nights,
			"total_amount": from_minor(total_minor, stay.currency),
			"average_rate": from_minor(total_minor // max(nights, 1), stay.currency),
		}
	)
	stay.flags[reservations.SERVICE_FLAG] = True
	stay.save(ignore_permissions=True)
	folio.refresh_stay_pending(stay.name)
	log_event(
		STAY,
		stay.name,
		"Early Departure",
		data={"booked_departure": str(booked_departure), "departure": str(new_departure)},
	)


def assert_guarantee_satisfied(stay) -> None:
	"""Check-in needs the booking's guarantee or deposit (F12 enforces it). Nothing to check yet."""


def assert_ready_to_check_out(stay, override_reason: str | None = None) -> None:
	"""Check-out needs every open folio at zero, or a Front Desk Manager's override."""
	folio.assert_folios_settled(stay, override_reason)


def _business_date(property_name: str):
	return getdate(frappe.db.get_value("Hotel Property", property_name, "business_date"))


# --------------------------------------------------------------------------- views


def front_desk_today(property_name: str) -> dict:
	"""Arrivals, in-house stays and departures for the property's business date."""
	business_date = _business_date(property_name)
	fields = [
		"name",
		"status",
		"hotel_booking",
		"lead_guest",
		"lead_guest_name",
		"room_type",
		"room_occupancy",
		"arrival_date",
		"departure_date",
		"nights",
		"adults",
		"children",
		"eta",
	]
	arrivals = frappe.get_all(
		STAY,
		filters={
			"property": property_name,
			"status": ["in", PRE_ARRIVAL_STATUSES],
			"arrival_date": ["<=", business_date],
			"departure_date": [">", business_date],
		},
		fields=fields,
		order_by="arrival_date asc, eta asc",
	)
	in_house = frappe.get_all(
		STAY,
		filters={"property": property_name, "status": ["in", IN_HOUSE_STATUSES]},
		fields=fields,
		order_by="departure_date asc",
	)
	departures = [stay for stay in in_house if getdate(stay.departure_date) <= business_date]
	_add_room_details([*arrivals, *in_house])
	return {
		"property": property_name,
		"business_date": business_date,
		"arrivals": arrivals,
		"in_house": in_house,
		"departures": departures,
	}


def _add_room_details(stays: list) -> None:
	occupancies = [stay.room_occupancy for stay in stays if stay.room_occupancy]
	assignments = {
		row.room_occupancy: row
		for row in frappe.get_all(
			ASSIGNMENT,
			filters={"room_occupancy": ["in", occupancies or [""]], "status": ["in", ACTIVE_ASSIGNMENTS]},
			fields=["room_occupancy", "hotel_room", "room_number", "do_not_move"],
		)
	}
	rooms = {
		row.name: row
		for row in frappe.get_all(
			HOTEL_ROOM,
			filters={"name": ["in", [a.hotel_room for a in assignments.values()] or [""]]},
			fields=["name", "housekeeping_condition"],
		)
	}
	type_names = dict(
		frappe.get_all(
			"Room Type",
			filters={"name": ["in", list({s.room_type for s in stays}) or [""]]},
			fields=["name", "room_type_name"],
			as_list=True,
		)
	)
	for stay in stays:
		assignment = assignments.get(stay.room_occupancy)
		room = rooms.get(assignment.hotel_room) if assignment else None
		stay["room_type_name"] = type_names.get(stay.room_type)
		stay["room"] = assignment.hotel_room if assignment else None
		stay["room_number"] = assignment.room_number if assignment else None
		stay["room_locked"] = bool(assignment and assignment.do_not_move)
		stay["room_condition"] = room.housekeeping_condition if room else None
		stay["room_ready"] = bool(room and room.housekeeping_condition in READY_CONDITIONS)


def stay_details(stay_name: str) -> dict:
	"""Reservation 360: the stay, its guests, its rooms over time, its nightly prices and its history."""
	stay = frappe.get_doc(STAY, stay_name)
	summary = stay.as_dict(no_default_fields=True)
	summary["name"] = stay.name
	_add_room_details([summary])
	summary["rate_plan_name"] = frappe.db.get_value("Rate Plan", stay.rate_plan, "rate_plan_name")
	summary["business_date"] = _business_date(stay.property)
	guests = frappe.get_all(
		STAY_GUEST,
		filters={"stay_reservation": stay.name},
		fields=[
			"name",
			"guest_profile",
			"guest_name",
			"role",
			"age_category",
			"status",
			"registration_complete",
			"actual_check_in",
			"actual_check_out",
		],
		order_by="creation asc",
	)
	assignments = frappe.get_all(
		ASSIGNMENT,
		filters={"stay_reservation": stay.name, "status": ["!=", "Cancelled"]},
		fields=[
			"name",
			"hotel_room",
			"room_number",
			"status",
			"do_not_move",
			"start_datetime",
			"end_datetime",
			"move_reason",
			"previous_assignment",
		],
		order_by="start_datetime asc, creation asc",
	)
	nights = frappe.get_all(
		RATE_NIGHT,
		filters={"stay_reservation": stay.name},
		fields=["night_date", "room_rate", "total", "posting_state"],
		order_by="night_date asc",
	)
	references = [stay.name, *(a.name for a in assignments), *(g.name for g in guests)]
	events = frappe.get_all(
		"Hospitality Event Log",
		filters={"reference_name": ["in", references]},
		fields=["event_type", "from_status", "to_status", "reason", "user", "timestamp", "reference_doctype"],
		order_by="timestamp desc, creation desc",
		limit=100,
	)
	folios = frappe.get_all(
		folio.FOLIO,
		filters={"stay_reservation": stay.name},
		fields=[
			"name",
			"folio_label",
			"status",
			"is_default",
			"payee_name",
			"balance",
			"pending_total",
			"currency",
		],
		order_by="window_number asc, creation asc",
	)
	owing = from_minor(
		sum(to_minor(row.balance, row.currency) for row in folios if row.status in folio.POSTABLE_STATUSES),
		stay.currency,
	)
	status = stay.status
	return {
		"stay": summary,
		"guests": guests,
		"assignments": assignments,
		"nights": nights,
		"events": events,
		"folios": folios,
		"open_balance": owing,
		"actions": {
			"can_assign": status in PRE_ARRIVAL_STATUSES,
			"can_check_in": status in PRE_ARRIVAL_STATUSES
			and getdate(stay.arrival_date) <= summary["business_date"] < getdate(stay.departure_date),
			"can_move": status in IN_HOUSE_STATUSES,
			"can_check_out": status in IN_HOUSE_STATUSES,
			"can_edit_guests": status in GUEST_EDITABLE_STATUSES,
			"can_view_folios": bool(folios) and bool(frappe.has_permission(folio.FOLIO, "read")),
			"can_override_check_out": bool(set(FOLIO_MANAGER_ROLES) & set(frappe.get_roles())),
		},
	}


# --------------------------------------------------------------------------- setup


def install_default_move_reasons() -> None:
	if not frappe.db.table_exists("Room Move Reason"):
		return
	for reason in DEFAULT_MOVE_REASONS:
		if not frappe.db.exists("Room Move Reason", reason):
			frappe.get_doc({"doctype": "Room Move Reason", "reason": reason}).insert(ignore_permissions=True)
