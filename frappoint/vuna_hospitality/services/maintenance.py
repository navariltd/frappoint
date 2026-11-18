"""Maintenance (design §20.2; feature F17): faults in rooms and their equipment.

A **Maintenance Request** records the issue, its severity (which sets how soon someone must
respond), who fixes it, and its resolution. When the fault makes the room unsellable, the request
puts the room **Out of Service** or **Out of Order** through a Room State Period, so inventory
changes as for any outage. Out of Order takes rooms out of inventory, so it needs a manager's
approval: one reported by anyone else waits as *Awaiting Approval*.

Resolving or cancelling the request ends its period on the business date (nights not yet reached
are given back), records the room nights lost, and leaves the room Dirty with a touch-up task, so
housekeeping checks it before it is sold again.

When the room or the failed equipment is an ERPNext **Asset**, the request opens an **Asset
Repair**: repair cost and downtime are kept there, not in the PMS.
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, date_diff, getdate, now_datetime

from frappoint.vuna_hospitality.constants import FRONT_DESK_MANAGER, HOSPITALITY_MANAGER
from frappoint.vuna_hospitality.services import housekeeping
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.property_scope import assert_property_access
from frappoint.vuna_hospitality.services.rooms import OUT_OF_ORDER, OUT_OF_SERVICE, mark_room

REQUEST = "Maintenance Request"
PERIOD = "Room State Period"
SERVICE_FLAG = "from_maintenance_service"

OPEN, AWAITING, IN_PROGRESS, RESOLVED, CANCELLED = (
	"Open",
	"Awaiting Approval",
	"In Progress",
	"Resolved",
	"Cancelled",
)
ACTIVE_STATUSES = (OPEN, AWAITING, IN_PROGRESS)
SEVERITIES = ("Low", "Medium", "High", "Critical")
# How soon someone must respond, by severity.
RESPONSE_HOURS = {"Critical": 4, "High": 24, "Medium": 72, "Low": 168}
NO_IMPACT = "None"
IMPACTS = (NO_IMPACT, OUT_OF_SERVICE, OUT_OF_ORDER)

MANAGER_ROLES = ("System Manager", HOSPITALITY_MANAGER, "Maintenance Manager", FRONT_DESK_MANAGER)
WORKER_ROLES = (*MANAGER_ROLES, "Maintenance User")
REPORTER_ROLES = (*WORKER_ROLES, *housekeeping.ATTENDANT_ROLES, "Front Desk Agent")


class MaintenanceError(frappe.ValidationError):
	pass


def _require(roles, action: str) -> None:
	if not set(roles) & set(frappe.get_roles()):
		raise frappe.PermissionError(_("You are not allowed to {0}.").format(action))


def can_manage(user: str | None = None) -> bool:
	return bool(set(MANAGER_ROLES) & set(frappe.get_roles(user)))


def _business_date(property_name: str):
	return getdate(frappe.db.get_value("Hotel Property", property_name, "business_date"))


def _request(name: str, *, lock: bool = True):
	if not frappe.db.exists(REQUEST, name):
		frappe.throw(_("Maintenance Request {0} does not exist.").format(name), frappe.DoesNotExistError)
	if lock:
		frappe.db.get_value(REQUEST, name, "name", for_update=True)
	doc = frappe.get_doc(REQUEST, name)
	assert_property_access(doc.property)
	return doc


def _save(doc, event: str, reason: str | None = None, **data) -> None:
	doc.flags[SERVICE_FLAG] = True
	doc.save(ignore_permissions=True)
	log_event(
		REQUEST,
		doc.name,
		event,
		to_status=doc.status,
		reason=reason,
		data={"room": doc.room_number, **data},
		property_name=doc.property,
	)


# --------------------------------------------------------------------------- reporting


def report(
	property_name: str,
	issue: str,
	*,
	room: str | None = None,
	asset: str | None = None,
	severity: str = "Medium",
	description: str | None = None,
	room_impact: str = NO_IMPACT,
	out_from=None,
	back_in_service_on=None,
	assigned_to: str | None = None,
	attachment: str | None = None,
) -> str:
	"""Record a fault. With a room impact, the room leaves sale now (or once a manager approves)."""
	_require(REPORTER_ROLES, _("report maintenance issues"))
	assert_property_access(property_name)
	issue = (issue or "").strip()
	if not issue:
		frappe.throw(_("Say what is wrong."), MaintenanceError)
	if severity not in SEVERITIES:
		frappe.throw(_("Severity must be one of: {0}.").format(", ".join(SEVERITIES)), MaintenanceError)
	room_impact = room_impact or NO_IMPACT
	if room_impact not in IMPACTS:
		frappe.throw(_("Room impact must be one of: {0}.").format(", ".join(IMPACTS)), MaintenanceError)
	info = None
	if room:
		info = frappe.db.get_value(ROOM_FIELDS[0], room, ROOM_FIELDS[1], as_dict=True)
		if not info or info.property != property_name:
			frappe.throw(_("Choose a room of this property."), MaintenanceError)
		asset = asset or info.asset
	if room_impact != NO_IMPACT and not room:
		frappe.throw(_("Choose the room that leaves sale."), MaintenanceError)
	today = _business_date(property_name)
	out_from = getdate(out_from) if out_from else today
	back_in_service_on = getdate(back_in_service_on) if back_in_service_on else None
	if room_impact != NO_IMPACT:
		if out_from < today:
			frappe.throw(_("A room can't leave sale before today."), MaintenanceError)
		back_in_service_on = back_in_service_on or add_days(out_from, 1)
		if back_in_service_on <= out_from:
			frappe.throw(_("The room must come back after it goes out."), MaintenanceError)

	now = now_datetime()
	needs_approval = room_impact == OUT_OF_ORDER and not can_manage()
	doc = frappe.get_doc(
		{
			"doctype": REQUEST,
			"property": property_name,
			"hotel_room": room,
			"room_number": info.room_number if info else None,
			"asset": asset,
			"issue": issue[:140],
			"description": (description or "").strip() or None,
			"severity": severity,
			"status": AWAITING if needs_approval else OPEN,
			"sla_due": add_to_date(now, hours=RESPONSE_HOURS[severity]),
			"assigned_to": assigned_to,
			"reported_by": frappe.session.user,
			"reported_on": now,
			"room_impact": room_impact,
			"out_from": out_from if room_impact != NO_IMPACT else None,
			"back_in_service_on": back_in_service_on if room_impact != NO_IMPACT else None,
			"attachment": attachment,
		}
	)
	doc.flags[SERVICE_FLAG] = True
	doc.insert(ignore_permissions=True)
	log_event(
		REQUEST,
		doc.name,
		"Maintenance Reported",
		to_status=doc.status,
		data={"room": doc.room_number, "severity": severity, "impact": room_impact},
		property_name=property_name,
	)
	if asset:
		_open_asset_repair(doc)
	if room_impact != NO_IMPACT and not needs_approval:
		_take_room_out(doc)
	return doc.name


ROOM_FIELDS = ("Hotel Room", ["name", "property", "room_number", "asset"])


def _open_asset_repair(doc) -> None:
	asset = frappe.db.get_value("Asset", doc.asset, ["name", "company"], as_dict=True)
	if not asset:
		return
	repair = frappe.get_doc(
		{
			"doctype": "Asset Repair",
			"asset": asset.name,
			"company": asset.company,
			"failure_date": doc.reported_on,
			"repair_status": "Pending",
			"description": "\n".join(
				filter(None, [doc.issue, doc.description, _("From {0}").format(doc.name)])
			),
		}
	)
	repair.insert(ignore_permissions=True)
	doc.db_set("asset_repair", repair.name)
	log_event(
		REQUEST,
		doc.name,
		"Asset Repair Opened",
		data={"asset_repair": repair.name},
		property_name=doc.property,
	)


def _take_room_out(doc) -> None:
	period = frappe.get_doc(
		{
			"doctype": PERIOD,
			"room": doc.hotel_room,
			"state": doc.room_impact,
			"from_date": doc.out_from,
			"to_date": doc.back_in_service_on,
			"reason": _("{0} ({1})").format(doc.issue, doc.name),
			"reported_by": doc.reported_by,
			"assigned_to": doc.assigned_to,
		}
	)
	period.flags.ignore_permissions = True
	period.insert()
	period.submit()
	doc.db_set("room_state_period", period.name)


def approve(request: str) -> str:
	"""A manager approves taking the room out of order."""
	_require(MANAGER_ROLES, _("approve taking a room out of order"))
	doc = _request(request)
	if doc.status != AWAITING:
		frappe.throw(_("Request {0} is {1}.").format(doc.name, _(doc.status)), MaintenanceError)
	today = _business_date(doc.property)
	if getdate(doc.out_from) < today:
		# Approved later than asked: the room leaves sale from today, for as long as was asked.
		nights = date_diff(doc.back_in_service_on, doc.out_from)
		doc.out_from, doc.back_in_service_on = today, add_days(today, max(nights, 1))
	doc.update({"status": OPEN, "approved_by": frappe.session.user, "approved_on": now_datetime()})
	_save(doc, "Out of Order Approved")
	_take_room_out(doc)
	return doc.name


def start(request: str) -> str:
	_require(WORKER_ROLES, _("work on maintenance requests"))
	doc = _request(request)
	if doc.status not in (OPEN,):
		frappe.throw(_("Request {0} is {1}.").format(doc.name, _(doc.status)), MaintenanceError)
	doc.status = IN_PROGRESS
	doc.assigned_to = doc.assigned_to or frappe.session.user
	_save(doc, "Maintenance Started")
	return doc.name


def assign(request: str, user: str | None) -> str:
	_require(MANAGER_ROLES, _("assign maintenance requests"))
	doc = _request(request)
	if doc.status not in ACTIVE_STATUSES:
		frappe.throw(_("Request {0} is {1}.").format(doc.name, _(doc.status)), MaintenanceError)
	if user and not frappe.db.exists("User", {"name": user, "enabled": 1}):
		frappe.throw(_("User {0} isn't active.").format(user), MaintenanceError)
	doc.assigned_to = user or None
	_save(doc, "Maintenance Assigned", assigned_to=user)
	return doc.name


def resolve(request: str, resolution: str) -> str:
	"""The fault is fixed: the room comes back from today and housekeeping checks it first."""
	_require(WORKER_ROLES, _("resolve maintenance requests"))
	resolution = (resolution or "").strip()
	if not resolution:
		frappe.throw(_("Say what was done."), MaintenanceError)
	doc = _request(request)
	if doc.status not in (OPEN, IN_PROGRESS):
		frappe.throw(_("Request {0} is {1}.").format(doc.name, _(doc.status)), MaintenanceError)
	doc.update(
		{
			"status": RESOLVED,
			"resolution": resolution,
			"resolved_by": frappe.session.user,
			"resolved_on": now_datetime(),
		}
	)
	_end_room_impact(doc)
	_save(doc, "Maintenance Resolved", reason=resolution, lost_room_nights=doc.lost_room_nights)
	return doc.name


def cancel(request: str, reason: str) -> str:
	"""Withdraw a request raised by mistake. Any outage it started ends today."""
	_require(MANAGER_ROLES, _("cancel maintenance requests"))
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for cancelling the request."), MaintenanceError)
	doc = _request(request)
	if doc.status not in ACTIVE_STATUSES:
		frappe.throw(_("Request {0} is {1}.").format(doc.name, _(doc.status)), MaintenanceError)
	doc.update({"status": CANCELLED, "cancel_reason": reason})
	_end_room_impact(doc)
	_save(doc, "Maintenance Cancelled", reason=reason)
	return doc.name


def _end_room_impact(doc) -> None:
	"""End the request's outage on the business date and count the out-of-order nights used."""
	if not doc.room_state_period:
		return
	period = frappe.get_doc(PERIOD, doc.room_state_period)
	if period.docstatus != 1:
		return
	today = _business_date(doc.property)
	from_date, to_date = getdate(period.from_date), getdate(period.to_date)
	ended = period.name
	if from_date >= today:
		# It hadn't started yet: give every night back.
		_cancel_period(period)
		ended, to_date = None, from_date
	elif to_date > today:
		# Started: keep the nights already out, give the rest back.
		_cancel_period(period)
		shorter = frappe.copy_doc(period)
		shorter.update(
			{
				"docstatus": 0,
				"amended_from": period.name,
				"to_date": today,
				"resolution_notes": doc.resolution,
			}
		)
		shorter.flags.ignore_permissions = True
		shorter.insert()
		shorter.submit()
		ended, to_date = shorter.name, today
	doc.room_state_period = ended
	doc.lost_room_nights = max(date_diff(to_date, from_date), 0) if doc.room_impact == OUT_OF_ORDER else 0
	if doc.hotel_room:
		mark_room(doc.hotel_room, housekeeping_condition="Dirty", reason=_("Back from maintenance"))
		housekeeping.create_task(
			doc.hotel_room,
			housekeeping.TOUCH_UP,
			source="Manual",
			priority="High",
			notes=_("Back from maintenance: {0}").format(doc.issue),
		)


def _cancel_period(period) -> None:
	period.flags.ignore_permissions = True
	period.cancel()


# --------------------------------------------------------------------------- reading


REQUEST_FIELDS = [
	"name",
	"hotel_room",
	"room_number",
	"asset",
	"issue",
	"description",
	"severity",
	"status",
	"sla_due",
	"assigned_to",
	"reported_by",
	"reported_on",
	"room_impact",
	"out_from",
	"back_in_service_on",
	"room_state_period",
	"asset_repair",
	"resolution",
	"resolved_on",
	"lost_room_nights",
	"attachment",
]


def requests(property_name: str, include_closed_days: int = 7) -> list[dict]:
	"""Open requests, and those closed in the last week, most urgent first."""
	since = now_datetime() - timedelta(days=include_closed_days)
	rows = frappe.get_all(
		REQUEST,
		filters={"property": property_name},
		or_filters={"status": ["in", ACTIVE_STATUSES], "modified": [">=", since]},
		fields=REQUEST_FIELDS,
	)
	now = now_datetime()
	rank = {name: index for index, name in enumerate(reversed(SEVERITIES))}
	for row in rows:
		row["overdue"] = row.status in ACTIVE_STATUSES and row.sla_due and row.sla_due < now
	rows.sort(
		key=lambda row: (
			row.status not in ACTIVE_STATUSES,
			row.status != AWAITING,
			rank.get(row.severity, 9),
			row.sla_due or now,
		)
	)
	return rows
