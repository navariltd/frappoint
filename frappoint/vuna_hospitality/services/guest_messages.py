"""Messages for in-house guests, and traces: dated follow-ups for a department (design §14.2 and §14.3;
plan F20).

- A **Guest Message** is taken for a stay (optionally for one guest on it) and stays Pending until
  it is delivered, in person or otherwise, or fails. Pending messages show on Front Desk Today and
  on the stay.
- A **Guest Trace** is a follow-up for a department on a date: "Arrange a cake on 14 Nov",
  "Confirm the airport pickup the day before departure". It shows in the department's list on its
  due date until it is resolved or cancelled.
"""

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

from frappoint.vuna_hospitality.constants import (
	FRONT_DESK_AGENT,
	FRONT_DESK_MANAGER,
	GUEST_SERVICES_AGENT,
	HOSPITALITY_MANAGER,
	HOUSEKEEPING_SUPERVISOR,
	NIGHT_AUDITOR,
)
from frappoint.vuna_hospitality.services.event_log import log_event

MESSAGE = "Guest Message"
TRACE = "Guest Trace"
STAY = "Stay Reservation"
SERVICE_FLAG = "from_guest_messages"

PENDING, DELIVERED, FAILED = "Pending", "Delivered", "Failed"
OPEN, RESOLVED, CANCELLED = "Open", "Resolved", "Cancelled"
CHANNELS = ("In Person", "SMS", "Email", "Portal")
DEPARTMENTS = ("Front Desk", "Housekeeping", "Concierge", "Food and Beverage", "Maintenance")
OPEN_STAY_STATUSES = ("Held", "Confirmed", "Due In", "In House", "Due Out")

MESSAGE_ROLES = (
	"System Manager",
	HOSPITALITY_MANAGER,
	FRONT_DESK_MANAGER,
	FRONT_DESK_AGENT,
	GUEST_SERVICES_AGENT,
	NIGHT_AUDITOR,
)
# Departments resolve their own traces.
TRACE_ROLES = (*MESSAGE_ROLES, HOUSEKEEPING_SUPERVISOR, "Maintenance Manager")


def _require(roles, what: str) -> None:
	if not set(roles) & set(frappe.get_roles()):
		raise frappe.PermissionError(_("You are not allowed to {0}.").format(what))


def _new(doctype: str, values: dict):
	doc = frappe.get_doc({"doctype": doctype, **values})
	doc.flags[SERVICE_FLAG] = True
	doc.insert(ignore_permissions=True)
	return doc


def _save(doc, values: dict) -> None:
	doc.update(values)
	doc.flags[SERVICE_FLAG] = True
	doc.save(ignore_permissions=True)


def _open_stay(stay_name: str) -> frappe._dict:
	stay = frappe.db.get_value(
		STAY, stay_name, ["name", "property", "status", "lead_guest_name"], as_dict=True
	)
	if not stay:
		raise frappe.DoesNotExistError(_("Stay {0} does not exist.").format(stay_name))
	if stay.status not in OPEN_STAY_STATUSES:
		frappe.throw(_("Stay {0} is {1}.").format(stay.name, _(stay.status)))
	return stay


# --------------------------------------------------------------------------- messages


def take_message(
	stay_name: str, message: str, sender: str | None = None, stay_guest: str | None = None
) -> str:
	_require(MESSAGE_ROLES, _("take guest messages"))
	stay = _open_stay(stay_name)
	message = (message or "").strip()
	if not message:
		frappe.throw(_("Write the message."))
	guest_name = stay.lead_guest_name
	if stay_guest:
		guest = frappe.db.get_value(
			"Stay Guest", stay_guest, ["stay_reservation", "guest_name"], as_dict=True
		)
		if not guest or guest.stay_reservation != stay.name:
			frappe.throw(_("That guest isn't on stay {0}.").format(stay.name))
		guest_name = guest.guest_name
	doc = _new(
		MESSAGE,
		{
			"property": stay.property,
			"stay_reservation": stay.name,
			"stay_guest": stay_guest,
			"guest_name": guest_name,
			"sender": (sender or "").strip() or None,
			"message": message,
			"status": PENDING,
			"taken_by": frappe.session.user,
			"taken_at": now_datetime(),
		},
	)
	log_event(STAY, stay.name, "Guest Message Taken", data={"message": doc.name})
	return doc.name


def close_message(
	name: str, delivered: bool = True, channel: str = "In Person", notes: str | None = None
) -> None:
	"""Mark a message delivered (by `channel`) or failed."""
	_require(MESSAGE_ROLES, _("deliver guest messages"))
	doc = frappe.get_doc(MESSAGE, name)
	if doc.status != PENDING:
		frappe.throw(_("Message {0} is already {1}.").format(doc.name, _(doc.status).lower()))
	if delivered and channel not in CHANNELS:
		frappe.throw(_("Say how the message was delivered."))
	if not delivered and not (notes or "").strip():
		frappe.throw(_("Say why the message couldn't be delivered."))
	_save(
		doc,
		{
			"status": DELIVERED if delivered else FAILED,
			"channel": channel if delivered else None,
			"delivered_by": frappe.session.user,
			"delivered_at": now_datetime(),
			"notes": (notes or "").strip() or None,
		},
	)
	log_event(
		STAY,
		doc.stay_reservation,
		"Guest Message Delivered" if delivered else "Guest Message Failed",
		data={"message": name},
	)


# --------------------------------------------------------------------------- traces


def add_trace(stay_name: str, department: str, due_date, text: str, due_time: str | None = None) -> str:
	_require(MESSAGE_ROLES, _("set traces"))
	stay = _open_stay(stay_name)
	if department not in DEPARTMENTS:
		frappe.throw(_("Pick the department that follows it up."))
	text = (text or "").strip()
	if not text:
		frappe.throw(_("Say what needs doing."))
	doc = _new(
		TRACE,
		{
			"property": stay.property,
			"stay_reservation": stay.name,
			"guest_name": stay.lead_guest_name,
			"department": department,
			"due_date": getdate(due_date),
			"due_time": due_time or None,
			"text": text,
			"status": OPEN,
			"created_by": frappe.session.user,
		},
	)
	log_event(STAY, stay.name, "Trace Set", data={"trace": doc.name, "department": department})
	return doc.name


def close_trace(name: str, resolved: bool = True, notes: str | None = None) -> None:
	"""Resolve a trace (done) or cancel it (no longer needed; give the reason)."""
	_require(TRACE_ROLES, _("resolve traces"))
	doc = frappe.get_doc(TRACE, name)
	if doc.status != OPEN:
		frappe.throw(_("Trace {0} is already {1}.").format(doc.name, _(doc.status).lower()))
	if not resolved and not (notes or "").strip():
		frappe.throw(_("Say why the trace is cancelled."))
	_save(
		doc,
		{
			"status": RESOLVED if resolved else CANCELLED,
			"resolved_by": frappe.session.user,
			"resolved_at": now_datetime(),
			"notes": (notes or "").strip() or None,
		},
	)
	log_event(
		STAY, doc.stay_reservation, "Trace Resolved" if resolved else "Trace Cancelled", data={"trace": name}
	)


# --------------------------------------------------------------------------- reading


def stay_messages(stay_name: str) -> dict:
	"""The stay's messages and traces, open ones first."""
	messages = frappe.get_all(
		MESSAGE,
		filters={"stay_reservation": stay_name},
		fields=[
			"name",
			"guest_name",
			"sender",
			"message",
			"status",
			"channel",
			"taken_by",
			"taken_at",
			"delivered_at",
			"notes",
		],
		order_by="taken_at desc",
	)
	traces = frappe.get_all(
		TRACE,
		filters={"stay_reservation": stay_name},
		fields=[
			"name",
			"department",
			"due_date",
			"due_time",
			"text",
			"status",
			"resolved_by",
			"resolved_at",
			"notes",
		],
		order_by="due_date asc, due_time asc",
	)
	order = {PENDING: 0, OPEN: 0}
	messages.sort(key=lambda row: order.get(row.status, 1))
	traces.sort(key=lambda row: order.get(row.status, 1))
	return {"messages": messages, "traces": traces}


def pending_counts(stay_names: list[str]) -> dict:
	"""{stay: {"messages": n, "traces": n}} of pending messages and open traces due by today."""
	counts = {name: {"messages": 0, "traces": 0} for name in stay_names}
	if not stay_names:
		return counts
	for row in frappe.get_all(
		MESSAGE, filters={"stay_reservation": ["in", stay_names], "status": PENDING}, pluck="stay_reservation"
	):
		counts[row]["messages"] += 1
	for row in frappe.get_all(
		TRACE, filters={"stay_reservation": ["in", stay_names], "status": OPEN}, pluck="stay_reservation"
	):
		counts[row]["traces"] += 1
	return counts


def traces_due(property_name: str, on_date, department: str | None = None) -> list[dict]:
	"""Open traces due by `on_date` (overdue ones included), for one department or all."""
	filters = {"property": property_name, "status": OPEN, "due_date": ["<=", getdate(on_date)]}
	if department:
		filters["department"] = department
	return frappe.get_all(
		TRACE,
		filters=filters,
		fields=["name", "stay_reservation", "guest_name", "department", "due_date", "due_time", "text"],
		order_by="due_date asc, due_time asc",
	)
