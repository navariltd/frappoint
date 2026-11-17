"""Tape chart endpoints (feature F16): the rooms-by-dates board, and dragging a stay to a room.

Reading needs read access to stays and the property. Dropping a stay is a front-desk command, like
assigning or moving a room on the stay page, and runs through the same service.
"""

import frappe
from frappe import _

from frappoint.vuna_hospitality.api.front_desk import FRONT_DESK_ROLES, STAY, _check_stay
from frappoint.vuna_hospitality.services import tape_chart
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.inventory import run_with_inventory_retry
from frappoint.vuna_hospitality.services.property_scope import assert_property_access


@frappe.whitelist()
@require_hospitality
def get_tape_chart(
	property: str, start: str | None = None, days: int | None = None, room_type: str | None = None
) -> dict:
	"""Rooms against dates for the window: assignments, outages and stays still without a room."""
	assert_property_access(property)
	if not frappe.has_permission(STAY, "read"):
		raise frappe.PermissionError(_("You are not allowed to see stays."))
	data = tape_chart.board(property, start, days, room_type or None)
	data["can_move"] = bool(set(FRONT_DESK_ROLES) & set(frappe.get_roles()))
	return data


@frappe.whitelist()
@require_hospitality
def check_drop(stay: str, room: str | None = None) -> dict:
	"""Whether dropping the stay on `room` (or on the unassigned lane) is allowed, before doing it."""
	_check_stay(stay, roles=None, permission="read")
	return tape_chart.check_drop(stay, room or None)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def drop_stay(
	stay: str, room: str | None = None, move_reason: str | None = None, notes: str | None = None
) -> dict:
	"""Assign the stay to `room`, move it there now, or (no room) take its room off."""
	_check_stay(stay, roles=FRONT_DESK_ROLES)
	result = run_with_inventory_retry(lambda: tape_chart.drop(stay, room or None, move_reason, notes))
	result["room_number"] = frappe.db.get_value("Hotel Room", room, "room_number") if room else None
	result["stay"] = stay
	result["guest"] = frappe.db.get_value(STAY, stay, "lead_guest_name")
	return result
