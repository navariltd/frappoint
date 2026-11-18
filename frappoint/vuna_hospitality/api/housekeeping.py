"""Housekeeping and maintenance endpoints (feature F17), for the Housekeeping Board.

Each command checks its own roles in the service: attendants work on their own tasks, supervisors
assign, inspect and plan, and maintenance staff work on requests. Out of Order needs a manager.
"""

import frappe
from frappe import _
from frappe.utils import cint

from frappoint.vuna_hospitality.services import housekeeping, maintenance
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.inventory import run_with_inventory_retry
from frappoint.vuna_hospitality.services.property_scope import assert_property_access

VIEW_ROLES = (*housekeeping.ATTENDANT_ROLES, *maintenance.WORKER_ROLES, "Front Desk Agent")


def _check_view(property_name: str) -> None:
	assert_property_access(property_name)
	if not set(VIEW_ROLES) & set(frappe.get_roles()):
		raise frappe.PermissionError(_("You are not allowed to see the housekeeping board."))


def _task_property(task: str) -> str:
	property_name = frappe.db.get_value(housekeeping.TASK, task, "property")
	if not property_name:
		raise frappe.DoesNotExistError(_("Housekeeping Task {0} does not exist.").format(task))
	assert_property_access(property_name)
	return property_name


def _board(property_name: str) -> dict:
	data = housekeeping.board(property_name)
	data["maintenance"] = maintenance.requests(property_name)
	data["can_manage_maintenance"] = maintenance.can_manage()
	data["can_work_maintenance"] = bool(set(maintenance.WORKER_ROLES) & set(frappe.get_roles()))
	data["can_report"] = bool(set(maintenance.REPORTER_ROLES) & set(frappe.get_roles()))
	data["refresh_seconds"] = max(
		cint(frappe.db.get_single_value("Hospitality Settings", "board_refresh_seconds")), 0
	)
	return data


@frappe.whitelist()
@require_hospitality
def get_housekeeping_board(property: str) -> dict:
	"""Rooms, today's tasks and staff, discrepancies, and maintenance requests."""
	_check_view(property)
	return _board(property)


# --------------------------------------------------------------------------- tasks


def _run_task(task: str, fn) -> dict:
	property_name = _task_property(task)
	run_with_inventory_retry(fn)
	return _board(property_name)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def plan_stayovers(property: str) -> dict:
	"""A stayover task for every occupied room whose guest stays tonight."""
	_check_view(property)
	run_with_inventory_retry(lambda: housekeeping.plan_stayovers(property))
	return _board(property)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def create_task(
	room: str,
	task_type: str,
	priority: str | None = None,
	notes: str | None = None,
	assigned_to: str | None = None,
) -> dict:
	property_name = frappe.db.get_value("Hotel Room", room, "property")
	if not property_name:
		raise frappe.DoesNotExistError(_("Room {0} does not exist.").format(room))
	assert_property_access(property_name)
	if not housekeeping.can_supervise():
		raise frappe.PermissionError(_("You are not allowed to add housekeeping tasks."))
	run_with_inventory_retry(
		lambda: housekeeping.create_task(
			room, task_type, priority=priority, notes=notes, assigned_to=assigned_to or None
		)
	)
	return _board(property_name)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def assign_task(task: str, employee: str | None = None) -> dict:
	property_name = _task_property(task)
	result = run_with_inventory_retry(lambda: housekeeping.assign(task, employee or None))
	return {**_board(property_name), "warnings": result["warnings"]}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def start_task(task: str) -> dict:
	return _run_task(task, lambda: housekeeping.start(task))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def finish_task(task: str, room_found: str | None = None, notes: str | None = None) -> dict:
	return _run_task(task, lambda: housekeeping.finish(task, room_found or None, notes))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def mark_do_not_disturb(task: str) -> dict:
	return _run_task(task, lambda: housekeeping.mark_do_not_disturb(task))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def inspect_task(task: str, passed: int, notes: str | None = None) -> dict:
	return _run_task(task, lambda: housekeeping.inspect(task, bool(cint(passed)), notes))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def cancel_task(task: str, reason: str) -> dict:
	return _run_task(task, lambda: housekeeping.cancel(task, reason))


# --------------------------------------------------------------------------- maintenance


def _run_request(request: str, fn) -> dict:
	property_name = frappe.db.get_value(maintenance.REQUEST, request, "property")
	if not property_name:
		raise frappe.DoesNotExistError(_("Maintenance Request {0} does not exist.").format(request))
	assert_property_access(property_name)
	run_with_inventory_retry(fn)
	return _board(property_name)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def report_maintenance(
	property: str,
	issue: str,
	room: str | None = None,
	asset: str | None = None,
	severity: str = "Medium",
	description: str | None = None,
	room_impact: str = "None",
	out_from: str | None = None,
	back_in_service_on: str | None = None,
	attachment: str | None = None,
) -> dict:
	"""Report a fault; with a room impact, the room leaves sale (Out of Order after approval)."""
	name = run_with_inventory_retry(
		lambda: maintenance.report(
			property,
			issue,
			room=room or None,
			asset=asset or None,
			severity=severity,
			description=description,
			room_impact=room_impact or "None",
			out_from=out_from or None,
			back_in_service_on=back_in_service_on or None,
			attachment=attachment or None,
		)
	)
	return {**_board(property), "request": name}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def approve_maintenance(request: str) -> dict:
	return _run_request(request, lambda: maintenance.approve(request))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def start_maintenance(request: str) -> dict:
	return _run_request(request, lambda: maintenance.start(request))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def resolve_maintenance(request: str, resolution: str) -> dict:
	return _run_request(request, lambda: maintenance.resolve(request, resolution))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def cancel_maintenance(request: str, reason: str) -> dict:
	return _run_request(request, lambda: maintenance.cancel(request, reason))
