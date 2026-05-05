import json

import frappe
from frappe import _

from ..doctype.service_provider_appointment_slot.service_provider_appointment_slot import get_available_slots


@frappe.whitelist(allow_guest=True)
def get_available_dates(service_type: str, duration: int, provider: str | None = None, days_ahead: int = 30):
	"""
	Get dates that have availability
	Use case: Calendar view, date picker
	"""

	slots = get_available_slots(
		appointment_type=service_type, duration=duration, provider=provider, days_ahead=days_ahead
	)

	# Extract unique dates
	available_dates = [d["date"] for d in slots]

	return sorted(list(available_dates))


@frappe.whitelist(allow_guest=True)
def get_available_time_slots(service_type, duration, provider=None, date=None, days_ahead=30):
	"""
	Get available time slots
	Use case: Main booking interface
	"""

	return get_available_slots(
		appointment_type=service_type, duration=duration, provider=provider, date=date, days_ahead=days_ahead
	)


@frappe.whitelist(allow_guest=True)
def check_slot_availability(slot_ids):
	"""
	Check if specific slots are still available before booking
	Use case: Pre-booking validation
	"""
	if isinstance(slot_ids, str):
		slot_ids = [s.strip() for s in slot_ids.split(",") if s.strip()]

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
