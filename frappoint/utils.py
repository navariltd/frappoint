import frappe
from frappe.utils import add_days, date_diff, getdate

from .frappoint.doctype.service_provider_appointment_slot.service_provider_appointment_slot import (
	generate_slots_for_specific_days,
)

SETTINGS = frappe.get_single("Service Appointment Settings")


def purge_old_slots():
	today = getdate()

	if SETTINGS.allow_past_booking:
		purge_date = date_diff(today, SETTINGS.max_past_days)
	else:
		purge_date = today

	frappe.db.delete("Service Provider Appointment Slot", {"posting_date": ["<", purge_date]})

	frappe.db.commit()
	return f"Purged slots older than {purge_date}"


def replenish_slot_window():
	today = getdate()
	window_end = add_days(today, SETTINGS.max_advance_days)

	active_shifts = frappe.get_all(
		"Service Provider Shift Assignment",
		filters={"status": "Active", "docstatus": 1},
		fields=["name", "start_date", "end_date"],
	)

	for shift in active_shifts:
		shift_start = max(today, shift.start_date)
		shift_end = min(shift.end_date or window_end, window_end)

		last_slot_date = frappe.db.get_value(
			"Service Provider Appointment Slot",
			{"shift_assignment": shift.name},
			"MAX(posting_date)",
		)

		gen_start = add_days(last_slot_date, 1) if last_slot_date else shift_start

		if gen_start > shift_end:
			continue

		weekdays = get_shift_weekdays(shift.name)

		generate_slots_for_specific_days(
			shift_assignment=shift.name, weekdays=weekdays, start_date=gen_start, end_date=shift_end
		)


def get_shift_weekdays(shift_assignment):
	"""
	Return weekday names expected by generate_slots_for_specific_days()
	Example: {"Monday", "Wednesday", "Friday"}
	"""

	sa = frappe.get_doc("Service Provider Shift Assignment", shift_assignment)

	DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

	# Daily shift all days
	if sa.repeat_type == "Daily":
		return set(DAYS)

	# Weekly shift checkbox-driven days
	if sa.repeat_type == "Weekly":
		day_fields = [
			"monday",
			"tuesday",
			"wednesday",
			"thursday",
			"friday",
			"saturday",
			"sunday",
		]

		selected_days = set()
		for idx, field in enumerate(day_fields):
			if sa.get(field):
				selected_days.add(DAYS[idx])

		return selected_days

	return set()
