"""Housekeeping (design §20.1; feature F17): room work, who does it, and when a room is ready.

A **Housekeeping Task** is one piece of room work: a departure clean, stayover, touch-up,
turndown, deep clean or guest request. Tasks are created:

- automatically when a guest checks out or moves rooms: the room they leave gets a Departure
  Clean, high priority when another guest arrives in it today;
- by planning stayovers for the day: one per occupied room the guest isn't leaving;
- by a supervisor, for anything else.

Tasks go to **HRMS Employees** (decision D-11): active employees of the property's company and,
when set, its housekeeping department. Those with a Shift Assignment covering the day are shown
as on shift; assigning someone off shift is allowed, with a warning.

The work moves the room's housekeeping condition (services/rooms.py): finishing a task makes the
room **Clean**; a supervisor's inspection makes it **Inspected**, or sends it back as **Dirty**.
A room is ready for a guest when it is Clean or Inspected, or only Inspected when the property
requires inspection before check-in. Attendants record what they found (occupied, vacant, do
not disturb), which feeds the front-desk/housekeeping discrepancy list.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime

from frappoint.vuna_hospitality.constants import (
	FRONT_DESK_MANAGER,
	HOSPITALITY_MANAGER,
	HOUSEKEEPING_ATTENDANT,
	HOUSEKEEPING_SUPERVISOR,
)
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.rooms import mark_room

TASK = "Housekeeping Task"
ROOM = "Hotel Room"
SERVICE_FLAG = "from_housekeeping_service"

DEPARTURE_CLEAN = "Departure Clean"
STAYOVER = "Stayover"
TOUCH_UP = "Touch-up"
TURNDOWN = "Turndown"
DEEP_CLEAN = "Deep Clean"
GUEST_REQUEST = "Guest Request"
TASK_TYPES = (DEPARTURE_CLEAN, STAYOVER, TOUCH_UP, TURNDOWN, DEEP_CLEAN, GUEST_REQUEST)
# Workload credits: a departure clean is one unit of an attendant's day.
CREDITS = {
	DEPARTURE_CLEAN: 1.0,
	STAYOVER: 0.5,
	TOUCH_UP: 0.25,
	TURNDOWN: 0.25,
	DEEP_CLEAN: 2.0,
	GUEST_REQUEST: 0.25,
}

OPEN, IN_PROGRESS, DONE, INSPECTED, CANCELLED = "Open", "In Progress", "Done", "Inspected", "Cancelled"
ACTIVE_STATUSES = (OPEN, IN_PROGRESS)
PRIORITY_ORDER = {"High": 0, "Normal": 1, "Low": 2}
FOUND_OPTIONS = ("Occupied", "Vacant", "Do Not Disturb")

READY_CONDITIONS = ("Inspected", "Clean")
INSPECTED_ONLY = ("Inspected",)

SUPERVISOR_ROLES = ("System Manager", HOSPITALITY_MANAGER, HOUSEKEEPING_SUPERVISOR, FRONT_DESK_MANAGER)
ATTENDANT_ROLES = (*SUPERVISOR_ROLES, HOUSEKEEPING_ATTENDANT)

# Front-desk occupancy statuses that mean a guest should be in the room tonight.
FRONT_DESK_OCCUPIED = ("Occupied", "Due Out")
FRONT_DESK_EMPTY = ("Vacant", "Reserved", "Due In")


class HousekeepingError(frappe.ValidationError):
	pass


# --------------------------------------------------------------------------- readiness


def ready_conditions(property_name: str) -> tuple[str, ...]:
	"""The housekeeping conditions in which a room of the property can take a guest."""
	if cint(frappe.db.get_value("Hotel Property", property_name, "require_inspection")):
		return INSPECTED_ONLY
	return READY_CONDITIONS


def is_ready(room: str) -> bool:
	row = frappe.db.get_value(ROOM, room, ["property", "housekeeping_condition"], as_dict=True)
	return bool(row) and row.housekeeping_condition in ready_conditions(row.property)


def readiness_text(property_name: str) -> str:
	return _("Inspected") if ready_conditions(property_name) == INSPECTED_ONLY else _("Clean or Inspected")


def can_supervise(user: str | None = None) -> bool:
	return bool(set(SUPERVISOR_ROLES) & set(frappe.get_roles(user)))


def _require(roles, action: str) -> None:
	if not set(roles) & set(frappe.get_roles()):
		raise frappe.PermissionError(_("You are not allowed to {0}.").format(action))


def _business_date(property_name: str):
	return getdate(frappe.db.get_value("Hotel Property", property_name, "business_date"))


# --------------------------------------------------------------------------- creating tasks


def create_task(
	room: str,
	task_type: str,
	*,
	source: str = "Manual",
	stay: str | None = None,
	priority: str | None = None,
	notes: str | None = None,
	task_date=None,
	assigned_to: str | None = None,
) -> str:
	"""Add a task for `room`, unless the same kind of task is already open for it that day."""
	if task_type not in TASK_TYPES:
		frappe.throw(_("Choose a task: {0}.").format(", ".join(TASK_TYPES)), HousekeepingError)
	info = frappe.db.get_value(
		ROOM, room, ["name", "property", "room_number", "room_type", "floor", "is_active"], as_dict=True
	)
	if not info:
		frappe.throw(_("Room {0} does not exist.").format(room), frappe.DoesNotExistError)
	task_date = getdate(task_date or _business_date(info.property))
	existing = frappe.db.get_value(
		TASK,
		{
			"hotel_room": room,
			"task_type": task_type,
			"task_date": task_date,
			"status": ["in", ACTIVE_STATUSES],
		},
		"name",
	)
	if existing:
		return existing
	doc = frappe.get_doc(
		{
			"doctype": TASK,
			"property": info.property,
			"hotel_room": room,
			"room_number": info.room_number,
			"room_type": info.room_type,
			"floor": info.floor,
			"task_type": task_type,
			"task_date": task_date,
			"status": OPEN,
			"priority": priority or "Normal",
			"credits": CREDITS[task_type],
			"source": source,
			"stay_reservation": stay,
			"notes": (notes or "").strip() or None,
		}
	)
	doc.flags[SERVICE_FLAG] = True
	doc.insert(ignore_permissions=True)
	log_event(
		ROOM,
		room,
		"Housekeeping Task Created",
		data={"task": doc.name, "task_type": task_type, "source": source, "stay": stay},
		property_name=info.property,
	)
	if assigned_to:
		assign(doc.name, assigned_to, check_roles=False)
	return doc.name


def on_room_vacated(room: str, stay: str | None, source: str) -> str:
	"""The guest left the room (check-out or a move): it needs a departure clean, urgently when
	another guest is due in it today."""
	property_name = frappe.db.get_value(ROOM, room, "property")
	today = _business_date(property_name)
	arriving = frappe.db.exists(
		"Room Assignment",
		{"hotel_room": room, "status": "Assigned", "start_date": today},
	)
	return create_task(
		room,
		DEPARTURE_CLEAN,
		source=source,
		stay=stay,
		priority="High" if arriving else "Normal",
		notes=_("Arrival today") if arriving else None,
	)


def plan_stayovers(property_name: str) -> list[str]:
	"""A stayover task for every occupied room whose guest isn't leaving today. Running it again
	adds only what is missing."""
	_require(SUPERVISOR_ROLES, _("plan housekeeping"))
	return stayover_tasks(property_name)


def stayover_tasks(property_name: str) -> list[str]:
	"""The stayover tasks for the property's business date, without the role check: night audit
	plans the new day's work once it has moved the date (F19)."""
	today = _business_date(property_name)
	rows = frappe.get_all(
		"Room Assignment",
		filters={"property": property_name, "status": "Occupied", "end_date": [">", today]},
		fields=["hotel_room", "stay_reservation"],
	)
	return [
		create_task(row.hotel_room, STAYOVER, source="Stayover Plan", stay=row.stay_reservation)
		for row in rows
	]


# --------------------------------------------------------------------------- staff


def employee_of(user: str | None = None) -> str | None:
	return frappe.db.get_value(
		"Employee", {"user_id": user or frappe.session.user, "status": "Active"}, "name"
	)


def staff(property_name: str, on_date=None) -> list[dict]:
	"""Employees who can take housekeeping work, with whether they're on shift and their load."""
	on_date = getdate(on_date or _business_date(property_name))
	prop = frappe.db.get_value(
		"Hotel Property", property_name, ["company", "housekeeping_department"], as_dict=True
	)
	filters = {"status": "Active", "company": prop.company}
	if prop.housekeeping_department:
		filters["department"] = prop.housekeeping_department
	employees = frappe.get_all(
		"Employee", filters=filters, fields=["name", "employee_name", "user_id"], order_by="employee_name"
	)
	on_shift = _on_shift([row.name for row in employees], on_date)
	load = {}
	for row in frappe.get_all(
		TASK,
		filters={
			"property": property_name,
			"task_date": on_date,
			"status": ["!=", CANCELLED],
			"assigned_to": ["is", "set"],
		},
		fields=["assigned_to", "credits", "status"],
	):
		entry = load.setdefault(row.assigned_to, {"credits": 0.0, "open": 0, "done": 0})
		entry["credits"] += flt(row.credits)
		entry["open" if row.status in ACTIVE_STATUSES else "done"] += 1
	return [
		{
			"employee": row.name,
			"employee_name": row.employee_name,
			"user": row.user_id,
			"on_shift": row.name in on_shift,
			"shift": on_shift.get(row.name),
			**load.get(row.name, {"credits": 0.0, "open": 0, "done": 0}),
		}
		for row in employees
	]


def _on_shift(employees: list[str], on_date) -> dict[str, str]:
	"""{employee: shift type} for those with an active Shift Assignment covering the day (HRMS)."""
	if not employees or not frappe.db.exists("DocType", "Shift Assignment"):
		return {}
	rows = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": ["in", employees],
			"docstatus": 1,
			"status": "Active",
			"start_date": ["<=", on_date],
		},
		fields=["employee", "shift_type", "end_date"],
	)
	return {
		row.employee: row.shift_type for row in rows if not row.end_date or getdate(row.end_date) >= on_date
	}


# --------------------------------------------------------------------------- the work


def _task(name: str, *, lock: bool = True):
	if not frappe.db.exists(TASK, name):
		frappe.throw(_("Housekeeping Task {0} does not exist.").format(name), frappe.DoesNotExistError)
	if lock:
		frappe.db.get_value(TASK, name, "name", for_update=True)
	return frappe.get_doc(TASK, name)


def _save(doc, event: str, reason: str | None = None, **data) -> None:
	doc.flags[SERVICE_FLAG] = True
	doc.save(ignore_permissions=True)
	log_event(
		TASK,
		doc.name,
		event,
		to_status=doc.status,
		reason=reason,
		data={"room": doc.room_number, **data},
		property_name=doc.property,
	)


def _may_work_on(doc) -> None:
	"""Attendants work on their own tasks, or take an unassigned one; supervisors on any."""
	_require(ATTENDANT_ROLES, _("work on housekeeping tasks"))
	if can_supervise():
		return
	mine = employee_of()
	if not mine:
		raise frappe.PermissionError(_("Your user isn't linked to an active Employee."))
	if doc.assigned_to and doc.assigned_to != mine:
		raise frappe.PermissionError(
			_("Room {0} is assigned to {1}.").format(doc.room_number, doc.employee_name or doc.assigned_to)
		)
	if not doc.assigned_to:
		doc.assigned_to = mine
		doc.employee_name = frappe.db.get_value("Employee", mine, "employee_name")


def assign(task: str, employee: str | None, *, check_roles: bool = True) -> dict:
	"""Give the task to an employee (or take it back with None). Returns {"warnings"}."""
	if check_roles:
		_require(SUPERVISOR_ROLES, _("assign housekeeping tasks"))
	doc = _task(task)
	if doc.status not in ACTIVE_STATUSES:
		frappe.throw(_("Task {0} is {1}.").format(doc.name, _(doc.status)), HousekeepingError)
	warnings = []
	name = None
	if employee:
		row = frappe.db.get_value("Employee", employee, ["employee_name", "status", "company"], as_dict=True)
		company = frappe.db.get_value("Hotel Property", doc.property, "company")
		if not row or row.status != "Active" or row.company != company:
			frappe.throw(_("Choose an active employee of {0}.").format(company), HousekeepingError)
		name = row.employee_name
		if employee not in _on_shift([employee], doc.task_date):
			warnings.append(_("{0} has no shift on {1}.").format(name, frappe.format(doc.task_date, "Date")))
	doc.assigned_to, doc.employee_name = employee or None, name
	_save(doc, "Housekeeping Task Assigned", employee=employee, warnings=warnings)
	return {"task": doc.name, "warnings": warnings}


def start(task: str) -> str:
	doc = _task(task)
	_may_work_on(doc)
	if doc.status != OPEN:
		frappe.throw(_("Task {0} is {1}.").format(doc.name, _(doc.status)), HousekeepingError)
	doc.status, doc.started_at, doc.do_not_disturb = IN_PROGRESS, now_datetime(), 0
	_save(doc, "Housekeeping Task Started")
	return doc.name


def mark_do_not_disturb(task: str) -> str:
	"""The guest has Do Not Disturb up: the task waits, and the room stays as it was."""
	doc = _task(task)
	_may_work_on(doc)
	if doc.status not in ACTIVE_STATUSES:
		frappe.throw(_("Task {0} is {1}.").format(doc.name, _(doc.status)), HousekeepingError)
	doc.status, doc.do_not_disturb, doc.room_found = OPEN, 1, "Do Not Disturb"
	_save(doc, "Housekeeping Do Not Disturb")
	return doc.name


def finish(task: str, room_found: str | None = None, notes: str | None = None) -> str:
	"""The work is done: the room is Clean. `room_found` is what the attendant saw."""
	doc = _task(task)
	_may_work_on(doc)
	if doc.status not in ACTIVE_STATUSES:
		frappe.throw(_("Task {0} is {1}.").format(doc.name, _(doc.status)), HousekeepingError)
	if room_found and room_found not in FOUND_OPTIONS:
		frappe.throw(_("Room found must be one of: {0}.").format(", ".join(FOUND_OPTIONS)), HousekeepingError)
	now = now_datetime()
	doc.update(
		{
			"status": DONE,
			"started_at": doc.started_at or now,
			"finished_at": now,
			"room_found": room_found or doc.room_found,
			"do_not_disturb": 0,
			"inspection_result": None,
		}
	)
	if notes:
		doc.notes = "\n".join(text for text in (doc.notes, notes.strip()) if text)
	_save(doc, "Housekeeping Task Done", room_found=room_found)
	mark_room(doc.hotel_room, housekeeping_condition="Clean", reason=_("{0} done").format(_(doc.task_type)))
	return doc.name


def inspect(task: str, passed: bool, notes: str | None = None) -> str:
	"""A supervisor checks the work: passed makes the room Inspected (ready); failed sends the task
	back to the attendant and the room back to Dirty."""
	_require(SUPERVISOR_ROLES, _("inspect rooms"))
	doc = _task(task)
	if doc.status != DONE:
		frappe.throw(
			_("Only finished tasks are inspected. Task {0} is {1}.").format(doc.name, _(doc.status)),
			HousekeepingError,
		)
	notes = (notes or "").strip() or None
	if not passed and not notes:
		frappe.throw(_("Say what needs redoing."), HousekeepingError)
	doc.update(
		{
			"inspection_result": "Passed" if passed else "Failed",
			"inspected_by": frappe.session.user,
			"inspected_at": now_datetime(),
			"inspection_notes": notes,
			"status": INSPECTED if passed else OPEN,
		}
	)
	if not passed:
		doc.started_at = doc.finished_at = None
	_save(doc, "Room Inspected" if passed else "Inspection Failed", reason=notes)
	mark_room(
		doc.hotel_room,
		housekeeping_condition="Inspected" if passed else "Dirty",
		reason=_("Inspection passed") if passed else _("Inspection failed: {0}").format(notes),
	)
	return doc.name


def cancel(task: str, reason: str) -> str:
	_require(SUPERVISOR_ROLES, _("cancel housekeeping tasks"))
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for cancelling the task."), HousekeepingError)
	doc = _task(task)
	if doc.status not in ACTIVE_STATUSES:
		frappe.throw(_("Task {0} is {1}.").format(doc.name, _(doc.status)), HousekeepingError)
	doc.status, doc.cancel_reason = CANCELLED, reason
	_save(doc, "Housekeeping Task Cancelled", reason=reason)
	return doc.name


# --------------------------------------------------------------------------- reading


def discrepancies(property_name: str, on_date=None) -> list[dict]:
	"""Rooms where what the attendant found disagrees with the front desk today."""
	on_date = getdate(on_date or _business_date(property_name))
	rows = frappe.get_all(
		TASK,
		filters={
			"property": property_name,
			"task_date": on_date,
			"room_found": ["in", ("Occupied", "Vacant")],
		},
		fields=["name", "hotel_room", "room_number", "room_found", "finished_at", "employee_name"],
		order_by="finished_at desc",
	)
	latest = {}
	for row in rows:
		latest.setdefault(row.hotel_room, row)
	statuses = {
		room.name: room.occupancy_status
		for room in frappe.get_all(
			ROOM, filters={"name": ["in", list(latest) or [""]]}, fields=["name", "occupancy_status"]
		)
	}
	result = []
	for room, row in latest.items():
		front_desk = statuses.get(room)
		if row.room_found == "Vacant" and front_desk in FRONT_DESK_OCCUPIED:
			kind, hint = _("Found vacant"), _("The front desk has a guest in this room. A skipper?")
		elif row.room_found == "Occupied" and front_desk in FRONT_DESK_EMPTY:
			kind, hint = _("Found occupied"), _("The front desk has no guest in this room. A sleeper?")
		else:
			continue
		result.append(
			{
				"room": room,
				"room_number": row.room_number,
				"front_desk": front_desk,
				"housekeeping": row.room_found,
				"kind": kind,
				"hint": hint,
				"task": row.name,
				"reported_by": row.employee_name,
				"reported_at": row.finished_at,
			}
		)
	return result


TASK_FIELDS = [
	"name",
	"hotel_room",
	"room_number",
	"room_type",
	"floor",
	"task_type",
	"task_date",
	"status",
	"priority",
	"credits",
	"source",
	"stay_reservation",
	"assigned_to",
	"employee_name",
	"do_not_disturb",
	"room_found",
	"started_at",
	"finished_at",
	"inspection_result",
	"inspection_notes",
	"notes",
]


def board(property_name: str, on_date=None) -> dict:
	"""Everything the Housekeeping Board shows for the day."""
	on_date = getdate(on_date or _business_date(property_name))
	types = {
		row.name: row
		for row in frappe.get_all(
			"Room Type",
			filters={"property": property_name},
			fields=["name", "room_type_name", "code", "sort_order"],
		)
	}
	rooms = frappe.get_all(
		ROOM,
		filters={"property": property_name, "is_active": 1},
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
	arrivals = set(
		frappe.get_all(
			"Room Assignment",
			filters={"property": property_name, "status": "Assigned", "start_date": on_date},
			pluck="hotel_room",
		)
	)
	departures = set(
		frappe.get_all(
			"Room Assignment",
			filters={"property": property_name, "status": "Occupied", "end_date": ["<=", on_date]},
			pluck="hotel_room",
		)
	)
	open_requests = {}
	for row in frappe.get_all(
		"Maintenance Request",
		filters={"property": property_name, "status": ["in", ("Open", "Awaiting Approval", "In Progress")]},
		fields=["hotel_room", "issue", "severity"],
	):
		open_requests.setdefault(row.hotel_room, []).append(row)
	ready = ready_conditions(property_name)
	for room in rooms:
		room["room_type_name"] = types.get(room.room_type, {}).get("room_type_name")
		room["arrival_today"] = room.name in arrivals
		room["departure_today"] = room.name in departures
		room["ready"] = room.housekeeping_condition in ready
		room["maintenance"] = open_requests.get(room.name, [])
	rooms.sort(
		key=lambda row: (
			types.get(row.room_type, {}).get("sort_order") or 0,
			cint(row.floor),
			_natural(row.room_number),
		)
	)
	tasks = frappe.get_all(
		TASK,
		filters={"property": property_name, "task_date": on_date, "status": ["!=", CANCELLED]},
		fields=TASK_FIELDS,
	)
	tasks.sort(key=lambda row: (PRIORITY_ORDER.get(row.priority, 1), _natural(row.room_number)))
	# Work left over from earlier days still needs doing.
	tasks += frappe.get_all(
		TASK,
		filters={"property": property_name, "task_date": ["<", on_date], "status": ["in", ACTIVE_STATUSES]},
		fields=TASK_FIELDS,
		order_by="task_date asc, room_number asc",
	)
	return {
		"property": property_name,
		"business_date": _business_date(property_name),
		"date": on_date,
		"ready_conditions": list(ready),
		"rooms": rooms,
		"tasks": tasks,
		"staff": staff(property_name, on_date),
		"discrepancies": discrepancies(property_name, on_date),
		"me": employee_of(),
		"can_supervise": can_supervise(),
		"task_types": list(TASK_TYPES),
	}


def _natural(value):
	text = str(value or "")
	return (0, int(text), text) if text.isdigit() else (1, 0, text)
