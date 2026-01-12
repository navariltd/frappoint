import json

import frappe
from frappe import _

from ..doctype.service_provider_appointment_slot.service_provider_appointment_slot import get_available_slots


@frappe.whitelist(allow_guest=True)
def get_available_dates(service_type, provider=None, days_ahead=30):
	"""
	Get dates that have availability
	Use case: Calendar view, date picker
	"""

	slots = get_available_slots(appointment_type=service_type, provider=provider, days_ahead=days_ahead)

	# Extract unique dates
	available_dates = set()
	for provider_data in slots:
		for date_data in provider_data.get("available_dates", []):
			available_dates.add(date_data["date"])

	return sorted(list(available_dates))


@frappe.whitelist(allow_guest=True)
def get_available_time_slots(service_type, provider=None, date=None, days_ahead=30):
	"""
	Get available time slots
	Use case: Main booking interface
	"""

	return get_available_slots(
		appointment_type=service_type, provider=provider, date=date, days_ahead=days_ahead
	)


@frappe.whitelist(allow_guest=True)
def check_slot_availability(slot_ids):
	"""
	Check if specific slots are still available before booking
	Use case: Pre-booking validation
	"""
	if isinstance(slot_ids, str):
		slot_ids = json.loads(slot_ids)

	unavailable = []
	for slot_id in slot_ids:
		slot = frappe.db.get_value(
			"Service Provider Appointment Slot",
			slot_id,
			["is_available", "service_appointment"],
			as_dict=True,
		)

		if not slot or not slot.is_available or slot.service_appointment:
			unavailable.append(slot_id)

	return {"available": len(unavailable) == 0, "unavailable_slots": unavailable}
