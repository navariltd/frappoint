"""Services charged to a hotel stay (feature F15): find a stay, charge a services booking to its
guests, take it back to desk payment, retry a failed posting, and waive a service fee.

Charging needs one of SERVICE_CHARGE_ROLES and the property; waiving a fee is for Front Desk
Managers. The folio postings themselves happen when an appointment is completed, cancelled, or
marked a no-show (services/service_charges.py).
"""

import json

import frappe
from frappe import _
from frappe.utils import cint

from frappoint.vuna_hospitality.services import service_charges
from frappoint.vuna_hospitality.services.feature_flag import is_hospitality_enabled, require_hospitality
from frappoint.vuna_hospitality.services.inventory import run_with_inventory_retry
from frappoint.vuna_hospitality.services.property_scope import assert_property_access


def _parse(value, default=None):
	if value in (None, ""):
		return default
	return json.loads(value) if isinstance(value, str) else value


def room_charge_context(booking_name: str | None) -> dict:
	"""What the services desk shows about a booking's hotel stay. Safe while hospitality is off."""
	if not is_hospitality_enabled():
		return {"enabled": False, "canCharge": False, "hotelStay": None}
	return {
		"enabled": service_charges.room_charge_enabled(),
		"canCharge": service_charges.can_charge_to_room(),
		"hotelStay": service_charges.booking_summary(booking_name) if booking_name else None,
	}


@frappe.whitelist()
@require_hospitality
def search_stays(text: str | None = None, property: str | None = None) -> list[dict]:
	"""Confirmed and in-house stays to charge services to, with their guests and open folios."""
	frappe.only_for(service_charges.SERVICE_CHARGE_ROLES)
	return service_charges.stay_options(text or "", property or None)


@frappe.whitelist()
@require_hospitality
def get_booking_room_charge(booking: str) -> dict:
	frappe.has_permission("Service Booking", "read", booking, throw=True)
	return room_charge_context(booking)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def charge_booking_to_room(booking: str, stay: str, assignments: str | list, confirm: int = 1) -> dict:
	"""Charge the booking to the stay's guests and, with `confirm`, confirm its appointments."""
	frappe.has_permission("Service Booking", "write", booking, throw=True)

	def run():
		service_charges.link_booking(booking, stay, _parse(assignments, []))
		confirmed = service_charges.confirm_booking(booking) if cint(confirm) else []
		return confirmed

	confirmed = run_with_inventory_retry(run)
	return {"confirmedAppointments": confirmed, **room_charge_context(booking)}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def release_booking_to_desk(booking: str, reason: str) -> dict:
	"""Stop charging the booking to the room: it is paid and invoiced at the services desk again."""
	frappe.has_permission("Service Booking", "write", booking, throw=True)
	run_with_inventory_retry(lambda: service_charges.unlink_booking(booking, reason))
	return room_charge_context(booking)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def retry_service_posting(appointment: str) -> dict:
	"""Post the participants of a completed appointment whose charge failed."""
	return run_with_inventory_retry(lambda: service_charges.retry_posting(appointment))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def waive_service_fee(participant: str, reason: str) -> dict:
	return run_with_inventory_retry(lambda: service_charges.waive_fee(participant, reason))


@frappe.whitelist()
@require_hospitality
def get_stay_services(stay: str) -> list[dict]:
	"""The services charged to a stay's guests."""
	property_name = frappe.db.get_value("Stay Reservation", stay, "property")
	if not property_name:
		raise frappe.DoesNotExistError(_("Stay Reservation {0} does not exist.").format(stay))
	assert_property_access(property_name)
	frappe.has_permission("Stay Reservation", "read", stay, throw=True)
	return service_charges.stay_services(stay)
