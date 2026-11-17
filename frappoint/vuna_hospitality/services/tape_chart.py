"""The tape chart (design §26.1, §14.1; feature F16): rooms against dates, the whole house at once.

One windowed read gives the board everything it draws:

- **rooms**, by room type, with their housekeeping condition and occupancy status;
- **bars**: room assignments that overlap the window. *Assigned* (a confirmed stay waiting for
  its guest), *Occupied* (in house), and *Released* (an earlier segment of a stay that moved);
- **outages**: submitted Room State Periods (Out of Order, Out of Service);
- **unassigned**: held and confirmed stays in the window that have no room yet.

Dropping a stay on a room goes through the same commands as the stay page (services/front_desk.py),
so the same locks, overlap and turnover checks, and audit apply:

- a confirmed stay that hasn't arrived is **assigned** the room (its old assignment is cancelled);
- an in-house stay is **moved** now, with a reason: the current segment ends and a new one starts;
- dropping a confirmed stay on the unassigned lane **unassigns** it.

`check_drop` runs the same checks without writing, so the board warns before anything changes.
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, getdate, now_datetime

from frappoint.vuna_hospitality.services import front_desk
from frappoint.vuna_hospitality.services.front_desk import (
	ASSIGNMENT,
	HOTEL_ROOM,
	IN_HOUSE_STATUSES,
	PRE_ARRIVAL_STATUSES,
	READY_CONDITIONS,
	current_assignment,
	stay_window,
)
from frappoint.vuna_hospitality.services.reservations import STAY

MIN_DAYS, MAX_DAYS, DEFAULT_DAYS = 7, 62, 14
MIN_REFRESH_SECONDS = 15
BAR_STATUSES = ("Assigned", "Occupied", "Released")
UNASSIGNED_STAY_STATUSES = ("Held", "Confirmed", "Due In")
STAY_FIELDS = [
	"name",
	"status",
	"lead_guest_name",
	"arrival_date",
	"departure_date",
	"adults",
	"children",
	"room_type",
	"hotel_booking",
	"rate_plan",
	"room_occupancy",
]

ASSIGN, MOVE, UNASSIGN = "assign", "move", "unassign"


class DropRefusedError(frappe.ValidationError):
	pass


def settings() -> frappe._dict:
	values = frappe.db.get_value(
		"Hospitality Settings",
		"Hospitality Settings",
		["tape_chart_days", "board_refresh_seconds"],
		as_dict=True,
	)
	days = cint(values.tape_chart_days) or DEFAULT_DAYS
	refresh = cint(values.board_refresh_seconds)
	return frappe._dict(
		days=max(MIN_DAYS, min(days, MAX_DAYS)),
		refresh_seconds=max(refresh, MIN_REFRESH_SECONDS) if refresh > 0 else 0,
	)


def window(property_name: str, start=None, days=None) -> tuple:
	business_date = getdate(frappe.db.get_value("Hotel Property", property_name, "business_date"))
	first = getdate(start) if start else business_date - timedelta(days=1)
	count = max(MIN_DAYS, min(cint(days) or settings().days, MAX_DAYS))
	return business_date, first, add_days(first, count)


def board(property_name: str, start=None, days=None, room_type: str | None = None) -> dict:
	"""Everything the tape chart draws for [start, start + days)."""
	business_date, first, end = window(property_name, start, days)
	room_types = frappe.get_all(
		"Room Type",
		filters={"property": property_name, "is_active": 1},
		fields=["name", "room_type_name", "code"],
		order_by="sort_order asc, room_type_name asc",
	)
	type_order = {row.name: index for index, row in enumerate(room_types)}
	room_filters = {"property": property_name, "is_active": 1}
	if room_type:
		room_filters["room_type"] = room_type
	rooms = frappe.get_all(
		HOTEL_ROOM,
		filters=room_filters,
		fields=[
			"name",
			"room_number",
			"room_type",
			"floor",
			"housekeeping_condition",
			"occupancy_status",
			"sellability",
		],
	)
	rooms.sort(key=lambda row: (type_order.get(row.room_type, 999), _natural(row.room_number)))
	room_names = [row.name for row in rooms] or [""]

	assignments = frappe.get_all(
		ASSIGNMENT,
		filters={
			"hotel_room": ["in", room_names],
			"status": ["in", BAR_STATUSES],
			"start_date": ["<", end],
			"end_date": [">=", first],
		},
		fields=[
			"name",
			"hotel_room",
			"room_number",
			"stay_reservation",
			"status",
			"do_not_move",
			"start_date",
			"end_date",
			"start_datetime",
			"end_datetime",
			"move_reason",
			"previous_assignment",
		],
		order_by="start_datetime asc",
	)
	stays = {
		row.name: row
		for row in frappe.get_all(
			STAY,
			filters={"name": ["in", list({row.stay_reservation for row in assignments}) or [""]]},
			fields=STAY_FIELDS,
		)
	}
	bars = []
	for row in assignments:
		stay = stays.get(row.stay_reservation)
		if not stay:
			continue
		# A released segment ended the day of the move; zero-night segments still draw as a sliver.
		bars.append(
			{
				"assignment": row.name,
				"room": row.hotel_room,
				"stay": stay.name,
				"guest": stay.lead_guest_name,
				"stay_status": stay.status,
				"status": row.status,
				"start": row.start_date,
				"end": row.end_date,
				"arrival": stay.arrival_date,
				"departure": stay.departure_date,
				"adults": stay.adults,
				"children": stay.children,
				"booking": stay.hotel_booking,
				"locked": bool(row.do_not_move),
				"move_reason": row.move_reason,
				"moved_from": bool(row.previous_assignment),
				"draggable": _draggable(stay.status, row.status, row.do_not_move),
			}
		)

	outages = frappe.get_all(
		"Room State Period",
		filters={
			"room": ["in", room_names],
			"docstatus": 1,
			"from_date": ["<", end],
			"to_date": [">", first],
		},
		fields=["name", "room", "state", "from_date", "to_date", "reason"],
	)

	unassigned = []
	candidates = frappe.get_all(
		STAY,
		filters={
			"property": property_name,
			"status": ["in", UNASSIGNED_STAY_STATUSES],
			"arrival_date": ["<", end],
			"departure_date": [">", first],
			**({"room_type": room_type} if room_type else {}),
		},
		fields=STAY_FIELDS,
		order_by="arrival_date asc, creation asc",
	)
	assigned_occupancies = set(
		frappe.get_all(
			ASSIGNMENT,
			filters={
				"room_occupancy": ["in", [row.room_occupancy for row in candidates] or [""]],
				"status": ["in", front_desk.ACTIVE_ASSIGNMENTS],
			},
			pluck="room_occupancy",
		)
	)
	type_names = {row.name: row.room_type_name for row in room_types}
	for stay in candidates:
		if stay.room_occupancy in assigned_occupancies:
			continue
		unassigned.append(
			{
				"stay": stay.name,
				"guest": stay.lead_guest_name,
				"stay_status": stay.status,
				"room_type": stay.room_type,
				"room_type_name": type_names.get(stay.room_type, stay.room_type),
				"arrival": stay.arrival_date,
				"departure": stay.departure_date,
				"adults": stay.adults,
				"children": stay.children,
				"booking": stay.hotel_booking,
				# A held stay gets its room once it is confirmed.
				"draggable": stay.status in PRE_ARRIVAL_STATUSES,
			}
		)

	config = settings()
	return {
		"property": property_name,
		"business_date": business_date,
		"start": first,
		"end": end,
		"days": [
			{"date": add_days(first, offset), "weekday": add_days(first, offset).strftime("%a")}
			for offset in range((end - first).days)
		],
		"room_types": room_types,
		"rooms": rooms,
		"bars": bars,
		"outages": outages,
		"unassigned": unassigned,
		"refresh_seconds": config.refresh_seconds,
		"default_days": config.days,
		"move_reasons": frappe.get_all(
			"Room Move Reason", filters={"is_active": 1}, pluck="name", order_by="reason asc"
		),
	}


def _natural(value: str):
	"""Room 9 before room 10."""
	text = str(value or "")
	return (0, int(text), text) if text.isdigit() else (1, 0, text)


def _draggable(stay_status: str, assignment_status: str, locked) -> bool:
	if cint(locked):
		return False
	if assignment_status == "Assigned":
		return stay_status in PRE_ARRIVAL_STATUSES
	if assignment_status == "Occupied":
		return stay_status in IN_HOUSE_STATUSES
	return False


# --------------------------------------------------------------------------- dropping


def drop_action(stay, room: str | None) -> str:
	if not room:
		if stay.status not in PRE_ARRIVAL_STATUSES:
			frappe.throw(
				_("Only a stay that hasn't arrived can go back to unassigned. {0} is {1}.").format(
					stay.name, _(stay.status)
				),
				DropRefusedError,
			)
		return UNASSIGN
	if stay.status in PRE_ARRIVAL_STATUSES:
		return ASSIGN
	if stay.status in IN_HOUSE_STATUSES:
		return MOVE
	frappe.throw(
		_("Stay {0} is {1}. Only confirmed and in-house stays change rooms.").format(
			stay.name, _(stay.status)
		),
		DropRefusedError,
	)


def check_drop(stay_name: str, room: str | None) -> dict:
	"""What dropping the stay on `room` would do, and whether it may: {allowed, action, reason,
	warnings, needs_reason}. Writes nothing."""
	stay = frappe.get_doc(STAY, stay_name)
	result = {"allowed": False, "action": None, "reason": None, "warnings": [], "needs_reason": False}
	try:
		action = drop_action(stay, room)
		result["action"] = action
		current = current_assignment(stay.room_occupancy)
		if action == UNASSIGN:
			if not current:
				frappe.throw(_("Stay {0} has no room yet.").format(stay.name), DropRefusedError)
			if current.do_not_move:
				frappe.throw(
					_("Room {0} is locked to this stay (Do Not Move). Unlock it first.").format(
						current.room_number
					),
					DropRefusedError,
				)
			result["allowed"] = True
			return result
		if current and current.hotel_room == room:
			frappe.throw(_("The stay is already in this room."), DropRefusedError)
		if current and current.do_not_move:
			frappe.throw(
				_("Room {0} is locked to this stay (Do Not Move). Unlock it first.").format(
					current.room_number
				),
				DropRefusedError,
			)
		if action == ASSIGN:
			start, end = stay_window(stay)
			info = front_desk._check_room(stay, room, start, end, stay.arrival_date, stay.departure_date)
			if info.housekeeping_condition not in READY_CONDITIONS:
				result["warnings"].append(
					_("Room {0} is {1} now; it must be Clean or Inspected by check-in.").format(
						info.room_number, _(info.housekeeping_condition)
					)
				)
		else:
			planned_end = get_datetime(current.end_datetime) if current else stay_window(stay)[1]
			business_date = getdate(frappe.db.get_value("Hotel Property", stay.property, "business_date"))
			info = front_desk._check_room(
				stay, room, now_datetime(), planned_end, business_date, stay.departure_date
			)
			if info.housekeeping_condition not in READY_CONDITIONS:
				frappe.throw(
					_("Room {0} is {1}, not ready for a guest.").format(
						info.room_number, _(info.housekeeping_condition)
					),
					DropRefusedError,
				)
			result["needs_reason"] = True
		result["allowed"] = True
	except frappe.ValidationError as error:
		result["reason"] = str(error)
	return result


def drop(stay_name: str, room: str | None, move_reason: str | None = None, notes: str | None = None) -> dict:
	"""Assign, move or unassign the stay, through the front-desk commands. Returns what was done."""
	stay = frappe.get_doc(STAY, stay_name)
	action = drop_action(stay, room)
	if action == UNASSIGN:
		front_desk.unassign_room(stay.name, notes or _("Unassigned on the tape chart"))
		return {"action": action, "assignment": None}
	if action == ASSIGN:
		return {"action": action, "assignment": front_desk.assign_room(stay.name, room, notes=notes)}
	if not move_reason:
		frappe.throw(_("Choose why the guest is moving."), DropRefusedError)
	return {"action": action, "assignment": front_desk.move_room(stay.name, room, move_reason, notes)}
