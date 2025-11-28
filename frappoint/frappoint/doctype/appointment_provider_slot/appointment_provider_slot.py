# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import date_diff, get_time, getdate


class AppointmentProviderSlot(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		end_time: DF.Time
		is_available: DF.Check
		is_break: DF.Check
		posting_date: DF.Date
		provider: DF.Link
		service_appointment: DF.Link | None
		shift_assignment: DF.Link
		start_time: DF.Time
	# end: auto-generated types
	pass


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def daterange(start_date, end_date):
	for n in range((end_date - start_date).days + 1):
		yield start_date + timedelta(n)


def get_global_slot_size():
	return frappe.db.get_single_value("Service Appointment Settings", "default_slot_size")


def get_global_max_advance_days():
	return frappe.db.get_single_value("Service Appointment Settings", "max_advance_days")


def insert_slot(provider, slot_date, start_time, end_time, shift_assignment):
	exists = frappe.db.exists(
		"Appointment Provider Slot",
		{"provider": provider, "posting_date": slot_date, "start_time": start_time, "end_time": end_time},
	)
	if exists:
		return

	frappe.get_doc(
		{
			"doctype": "Appointment Provider Slot",
			"provider": provider,
			"posting_date": slot_date,
			"start_time": start_time,
			"end_time": end_time,
			"shift_assignment": shift_assignment,
		}
	).insert(ignore_permissions=True)


@frappe.whitelist()
def generate_for_shift(shift_assignment):
	sa = frappe.get_doc("Provider Shift Assignment", shift_assignment)
	st = frappe.get_doc("Provider Shift Type", sa.shift_type)

	if sa.status == "Inactive":
		frappe.db.set_value(
			"Appointment Provider Slot", {"shift_assignment": shift_assignment}, "is_available", 0
		)
		frappe.db.commit()
		return "Slots marked as unavailable"

	frappe.db.delete("Appointment Provider Slot", {"shift_assignment": shift_assignment})
	frappe.db.commit()

	provider = sa.provider
	slot_size = get_global_slot_size()
	holiday_list = st.holiday_list
	max_advance_days = get_global_max_advance_days()

	start_date = sa.start_date
	end_date = sa.end_date or (start_date + timedelta(days=max_advance_days))

	holidays = set()
	# Batch fetch holidays
	if holiday_list:
		holiday_records = frappe.db.get_all(
			"Holiday",
			filters={"parent": holiday_list, "holiday_date": ["between", [start_date, end_date]]},
			pluck="holiday_date",
		)
		holidays = set(holiday_records)

	# allowed weekdays for weekly repeat
	allowed_weekdays = set()
	if sa.repeat_type == "Weekly":
		for row in sa.days:
			allowed_weekdays.add(DAYS.index(row.weekday))

	slots_to_insert = []

	# Detect break overlap
	def slot_overlaps_break(start_t, end_t):
		if not st.break_start_time or not st.break_end_time:
			return False

		br_start = get_time(st.break_start_time)
		br_end = get_time(st.break_end_time)

		# Overlap if times intersect
		return (start_t < br_end) and (end_t > br_start)

	for dt in daterange(start_date, end_date):
		# Holiday check
		if dt in holidays:
			continue

		if sa.repeat_type == "None" and dt != start_date:
			continue

		if sa.repeat_type == "Weekly" and dt.weekday() not in allowed_weekdays:
			continue

		cursor = datetime.combine(dt, get_time(st.start_time))
		end_dt = datetime.combine(dt, get_time(st.end_time))

		while cursor < end_dt:
			start_t = cursor.time()
			end_t = (cursor + timedelta(minutes=slot_size)).time()

			if end_t > get_time(st.end_time):
				break

			if slot_overlaps_break(start_t, end_t):
				cursor += timedelta(minutes=slot_size)
				continue

			slots_to_insert.append(
				{
					"doctype": "Appointment Provider Slot",
					"provider": provider,
					"posting_date": dt,
					"start_time": start_t,
					"end_time": end_t,
					"shift_assignment": sa.name,
					"is_available": 1,
					"is_break": 0,
				}
			)

			cursor += timedelta(minutes=slot_size)

	if slots_to_insert:
		for slot in slots_to_insert:
			frappe.get_doc(slot).insert(ignore_permissions=True)
		frappe.db.commit()

	return f"Slots generated: {len(slots_to_insert)}"


def purge_old_slots():
	settings = frappe.get_single("Service Appointment Settings")

	today = getdate()

	if settings.allow_past_booking:
		purge_date = date_diff(today, settings.max_past_days)
	else:
		purge_date = today

	frappe.db.delete("Appointment Provider Slot", {"posting_date": ["<", purge_date]})

	frappe.db.commit()
	return f"Purged slots older than {purge_date}"


def generate_slots_for_specific_days(shift_assignment, weekdays):
	"""Generate slots only for specific weekdays"""
	sa = frappe.get_doc("Provider Shift Assignment", shift_assignment)
	st = frappe.get_doc("Provider Shift Type", sa.shift_type)

	if sa.status == "Inactive":
		return

	provider = sa.provider
	slot_size = get_global_slot_size()
	holiday_list = st.holiday_list
	max_advance_days = get_global_max_advance_days()

	start_date = sa.start_date
	end_date = sa.end_date or (start_date + timedelta(days=max_advance_days))

	# Map weekday names to indices
	weekday_indices = {DAYS.index(day) for day in weekdays}

	# Batch fetch holidays once
	holidays = set()
	if holiday_list:
		holiday_records = frappe.db.get_all(
			"Holiday",
			filters={"parent": holiday_list, "holiday_date": ["between", [start_date, end_date]]},
			pluck="holiday_date",
		)
		holidays = set(holiday_records)

	slots_to_insert = []

	def slot_overlaps_break(start_t, end_t):
		if not st.break_start_time or not st.break_end_time:
			return False
		br_start = get_time(st.break_start_time)
		br_end = get_time(st.break_end_time)
		return (start_t < br_end) and (end_t > br_start)

	for dt in daterange(start_date, end_date):
		# Only process specified weekdays
		if dt.weekday() not in weekday_indices:
			continue

		if dt in holidays:
			continue

		cursor = datetime.combine(dt, get_time(st.start_time))
		end_dt = datetime.combine(dt, get_time(st.end_time))

		while cursor < end_dt:
			start_t = cursor.time()
			end_t = (cursor + timedelta(minutes=slot_size)).time()

			if end_t > get_time(st.end_time):
				break

			if slot_overlaps_break(start_t, end_t):
				cursor += timedelta(minutes=slot_size)
				continue

			# Check if slot already exists
			exists = frappe.db.exists(
				"Appointment Provider Slot",
				{"provider": provider, "posting_date": dt, "start_time": start_t, "end_time": end_t},
			)

			if not exists:
				slots_to_insert.append(
					{
						"doctype": "Appointment Provider Slot",
						"provider": provider,
						"posting_date": dt,
						"start_time": start_t,
						"end_time": end_t,
						"shift_assignment": sa.name,
						"is_available": 1,
						"is_break": 0,
					}
				)

			cursor += timedelta(minutes=slot_size)

	# Bulk insert all slots
	if slots_to_insert:
		for slot in slots_to_insert:
			frappe.get_doc(slot).insert(ignore_permissions=True)
		frappe.db.commit()

	return f"Generated {len(slots_to_insert)} new slots for {', '.join(weekdays)}"


def delete_slots_for_specific_days(shift_assignment, weekdays):
	"""Delete slots only for specific weekdays (only unbooked slots)"""
	sa = frappe.get_doc("Provider Shift Assignment", shift_assignment)

	start_date = sa.start_date
	end_date = sa.end_date or (start_date + timedelta(days=get_global_max_advance_days()))

	# Map weekday names to Python indices (0=Monday, 6=Sunday)
	weekday_indices = [DAYS.index(day) for day in weekdays]

	# Get all dates that match the weekdays in the date range
	dates_to_delete = []
	for dt in daterange(start_date, end_date):
		if dt.weekday() in weekday_indices:
			dates_to_delete.append(dt)

	if not dates_to_delete:
		return f"No slots found for {', '.join(weekdays)}"

	# Delete unbooked slots for these specific dates
	deleted_count = frappe.db.sql(
		"""
		DELETE FROM `tabAppointment Provider Slot`
		WHERE shift_assignment = %s
		AND (service_appointment IS NULL OR service_appointment = '')
		AND posting_date IN %s
	""",
		(shift_assignment, dates_to_delete),
	)

	frappe.db.commit()

	count = deleted_count if isinstance(deleted_count, int) else len(dates_to_delete)
	return f"Deleted slots for {', '.join(weekdays)} ({count} dates processed)"
