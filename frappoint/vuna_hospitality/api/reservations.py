"""Reservation endpoints for the booking desk: hold, confirm, cancel, and read a booking.

Each command owns its request's transaction, so it runs through `run_with_inventory_retry`: if
another booking changed the same inventory rows meanwhile, it starts again and sees that booking.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint

from frappoint.vuna_hospitality.constants import RESERVATION_ROLES
from frappoint.vuna_hospitality.services import reservations
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.inventory import run_with_inventory_retry
from frappoint.vuna_hospitality.services.property_scope import assert_property_access


def _parse(value, default=None):
	if value in (None, ""):
		return default
	return json.loads(value) if isinstance(value, str) else value


def _check_can_book(property_name: str) -> None:
	frappe.only_for(RESERVATION_ROLES)
	assert_property_access(property_name)


def _check_stay(stay: str) -> None:
	_check_can_book(frappe.db.get_value(reservations.STAY, stay, "property"))
	if not frappe.has_permission(reservations.STAY, "write", doc=stay):
		raise frappe.PermissionError(_("You are not allowed to change stay {0}.").format(stay))


def _check_booking(booking: str, permission: str = "write") -> None:
	property_name = frappe.db.get_value(reservations.BOOKING, booking, "property")
	if not property_name:
		raise frappe.DoesNotExistError(_("Hotel Booking {0} does not exist.").format(booking))
	assert_property_access(property_name)
	if not frappe.has_permission(reservations.BOOKING, permission, doc=booking):
		raise frappe.PermissionError(_("You are not allowed to see booking {0}.").format(booking))


@frappe.whitelist()
@require_hospitality
def get_booking_desk_context() -> dict:
	"""What the new-reservation screen needs: the user's properties, booking sources, and limits."""
	properties = frappe.get_list(
		"Hotel Property",
		filters={"is_active": 1},
		fields=["name", "property_name", "business_date", "currency", "check_in_time", "check_out_time"],
		order_by="property_name asc",
	)
	sources = frappe.get_all(
		"Hotel Booking Source", filters={"is_active": 1}, pluck="name", order_by="source_name asc"
	)
	limits = reservations._limits()
	return {
		"properties": properties,
		"booking_sources": sources,
		"hold_expiry_minutes": limits.hold_minutes,
		"max_stay_nights": limits.max_stay_nights,
		"can_book": bool(set(frappe.get_roles()) & set(RESERVATION_ROLES)),
	}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def hold_stays(property: str, stays, booking: str | None = None, booking_details=None) -> dict:
	"""Hold rooms for one or more stays (all or none). Returns the booking with its stays."""
	_check_can_book(property)
	if booking:
		_check_booking(booking)
	stays, booking_details = _parse(stays, []), _parse(booking_details, {})
	return run_with_inventory_retry(lambda: reservations.hold(property, stays, booking, booking_details))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def confirm_stay(stay: str) -> dict:
	"""Confirm a held stay."""
	_check_stay(stay)
	return run_with_inventory_retry(lambda: reservations.confirm(stay))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def confirm_booking(booking: str) -> dict:
	"""Confirm every held stay on a booking."""
	_check_booking(booking)
	frappe.only_for(RESERVATION_ROLES)
	return run_with_inventory_retry(lambda: reservations.confirm_booking(booking))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def cancel_stay(stay: str, reason: str) -> dict:
	"""Cancel a held or confirmed stay and release its rooms."""
	_check_stay(stay)
	return run_with_inventory_retry(lambda: reservations.cancel(stay, reason))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def cancel_booking(booking: str, reason: str) -> dict:
	"""Cancel every held or confirmed stay on a booking."""
	_check_booking(booking)
	frappe.only_for(RESERVATION_ROLES)
	return run_with_inventory_retry(lambda: reservations.cancel_booking(booking, reason))


@frappe.whitelist()
@require_hospitality
def get_booking(booking: str) -> dict:
	"""A booking and its stays."""
	_check_booking(booking, "read")
	return reservations.booking_summary(booking)


@frappe.whitelist()
@require_hospitality
def get_recent_bookings(property: str, limit: int = 20) -> list[dict]:
	"""The property's latest bookings, newest first."""
	assert_property_access(property)
	return frappe.get_list(
		reservations.BOOKING,
		filters={"property": property},
		fields=[
			"name",
			"status",
			"booker_name",
			"booking_source",
			"total_amount",
			"currency",
			"stay_count",
			"creation",
		],
		order_by="creation desc",
		limit_page_length=max(1, min(cint(limit) or 20, 100)),
	)
