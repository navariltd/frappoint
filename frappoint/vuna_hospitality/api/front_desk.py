"""Front desk endpoints: Front Desk Today, Reservation 360, stay guests, rooms, check-in and check-out.

Room and arrival commands are for front-desk roles; guest lists can also be kept by reservations
agents. Every command owns its request's transaction and runs through `run_with_inventory_retry`.
"""

import frappe
from frappe import _
from frappe.utils import sbool

from frappoint.vuna_hospitality.constants import (
	FRONT_DESK_AGENT,
	FRONT_DESK_MANAGER,
	HOSPITALITY_MANAGER,
	RESERVATION_ROLES,
)
from frappoint.vuna_hospitality.services import front_desk
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.inventory import run_with_inventory_retry
from frappoint.vuna_hospitality.services.property_scope import assert_property_access

FRONT_DESK_ROLES = ("System Manager", HOSPITALITY_MANAGER, FRONT_DESK_MANAGER, FRONT_DESK_AGENT)
STAY = "Stay Reservation"


def _check_stay(stay: str, roles=FRONT_DESK_ROLES, permission: str = "write") -> None:
	property_name = frappe.db.get_value(STAY, stay, "property")
	if not property_name:
		raise frappe.DoesNotExistError(_("Stay Reservation {0} does not exist.").format(stay))
	if roles:
		frappe.only_for(roles)
	assert_property_access(property_name)
	if not frappe.has_permission(STAY, permission, doc=stay):
		raise frappe.PermissionError(_("You are not allowed to change stay {0}.").format(stay))


def _stay_of_guest(stay_guest: str) -> str:
	stay = frappe.db.get_value(front_desk.STAY_GUEST, stay_guest, "stay_reservation")
	if not stay:
		raise frappe.DoesNotExistError(_("Stay Guest {0} does not exist.").format(stay_guest))
	return stay


def _run(fn, stay: str) -> dict:
	run_with_inventory_retry(fn)
	return front_desk.stay_details(stay)


@frappe.whitelist()
@require_hospitality
def get_front_desk_today(property: str) -> dict:
	"""Arrivals, in-house stays and departures for the property's business date."""
	assert_property_access(property)
	if not frappe.has_permission(STAY, "read"):
		raise frappe.PermissionError(_("You are not allowed to see stays."))
	return front_desk.front_desk_today(property)


@frappe.whitelist()
@require_hospitality
def get_stay(stay: str) -> dict:
	"""Reservation 360 for one stay."""
	_check_stay(stay, roles=None, permission="read")
	return front_desk.stay_details(stay)


@frappe.whitelist()
@require_hospitality
def get_assignable_rooms(stay: str) -> list[dict]:
	"""Rooms of the stay's type, with availability and readiness."""
	_check_stay(stay, roles=None, permission="read")
	return front_desk.get_assignable_rooms(stay)


@frappe.whitelist()
@require_hospitality
def get_move_reasons() -> list[str]:
	return frappe.get_all("Room Move Reason", filters={"is_active": 1}, pluck="name", order_by="reason asc")


@frappe.whitelist(methods=["POST"])
@require_hospitality
def assign_room(stay: str, room: str, lock: bool = False) -> dict:
	_check_stay(stay)
	return _run(lambda: front_desk.assign_room(stay, room, lock=sbool(lock)), stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def unassign_room(stay: str, reason: str | None = None) -> dict:
	_check_stay(stay)
	return _run(lambda: front_desk.unassign_room(stay, reason), stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def set_room_lock(stay: str, locked: bool, reason: str | None = None) -> dict:
	_check_stay(stay)
	return _run(lambda: front_desk.set_room_lock(stay, sbool(locked), reason), stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def move_room(stay: str, room: str, move_reason: str, notes: str | None = None) -> dict:
	_check_stay(stay)
	return _run(lambda: front_desk.move_room(stay, room, move_reason, notes), stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def check_in(stay: str, room: str | None = None) -> dict:
	_check_stay(stay)
	return _run(lambda: front_desk.check_in(stay, room), stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def check_out(stay: str, override_reason: str | None = None) -> dict:
	"""Check out. With a balance on a folio, a Front Desk Manager must give `override_reason`."""
	_check_stay(stay)
	return _run(lambda: front_desk.check_out(stay, override_reason=override_reason), stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def add_stay_guest(
	stay: str, guest_profile: str, age_category: str = "Adult", guardian: str | None = None
) -> dict:
	_check_stay(stay, roles=RESERVATION_ROLES)
	return _run(
		lambda: front_desk.add_stay_guest(stay, guest_profile, age_category=age_category, guardian=guardian),
		stay,
	)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def remove_stay_guest(stay_guest: str, reason: str) -> dict:
	stay = _stay_of_guest(stay_guest)
	_check_stay(stay, roles=RESERVATION_ROLES)
	return _run(lambda: front_desk.remove_stay_guest(stay_guest, reason), stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def set_primary_guest(stay_guest: str, reason: str | None = None) -> dict:
	stay = _stay_of_guest(stay_guest)
	_check_stay(stay, roles=RESERVATION_ROLES)
	return _run(lambda: front_desk.set_primary_guest(stay_guest, reason), stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def register_guest(stay_guest: str) -> dict:
	stay = _stay_of_guest(stay_guest)
	_check_stay(stay)
	return _run(lambda: front_desk.register_guest(stay_guest), stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def check_in_guest(stay_guest: str) -> dict:
	stay = _stay_of_guest(stay_guest)
	_check_stay(stay)
	return _run(lambda: front_desk.check_in_guest(stay_guest), stay)
