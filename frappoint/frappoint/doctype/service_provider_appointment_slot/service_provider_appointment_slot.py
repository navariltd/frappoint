# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, get_datetime, get_time, getdate, now_datetime, nowdate


class ServiceProviderAppointmentSlot(Document):
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
		service_unit: DF.Link | None
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
		"Service Provider Appointment Slot",
		{"provider": provider, "posting_date": slot_date, "start_time": start_time, "end_time": end_time},
	)
	if exists:
		return

	frappe.get_doc(
		{
			"doctype": "Service Provider Appointment Slot",
			"provider": provider,
			"posting_date": slot_date,
			"start_time": start_time,
			"end_time": end_time,
			"shift_assignment": shift_assignment,
		}
	).insert(ignore_permissions=True)


@frappe.whitelist()
def generate_for_shift(shift_assignment):
	sa = frappe.get_doc("Service Provider Shift Assignment", shift_assignment)
	st = frappe.get_doc("Service Provider Shift Type", sa.shift_type)

	if sa.status == "Inactive":
		frappe.db.set_value(
			"Service Provider Appointment Slot", {"shift_assignment": shift_assignment}, "is_available", 0
		)
		frappe.db.commit()
		return "Slots marked as unavailable"

	frappe.db.delete("Service Provider Appointment Slot", {"shift_assignment": shift_assignment})
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
		day_fields = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
		for idx, day_field in enumerate(day_fields):
			if sa.get(day_field):
				allowed_weekdays.add(idx)

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
					"doctype": "Service Provider Appointment Slot",
					"provider": provider,
					"service_unit": sa.service_unit,
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

	frappe.db.delete("Service Provider Appointment Slot", {"posting_date": ["<", purge_date]})

	frappe.db.commit()
	return f"Purged slots older than {purge_date}"


def generate_slots_for_specific_days(shift_assignment, weekdays):
	"""Generate slots only for specific weekdays"""
	sa = frappe.get_doc("Service Provider Shift Assignment", shift_assignment)
	st = frappe.get_doc("Service Provider Shift Type", sa.shift_type)

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
				"Service Provider Appointment Slot",
				{"provider": provider, "posting_date": dt, "start_time": start_t, "end_time": end_t},
			)

			if not exists:
				slots_to_insert.append(
					{
						"doctype": "Service Provider Appointment Slot",
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
	sa = frappe.get_doc("Service Provider Shift Assignment", shift_assignment)

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
		DELETE FROM `tabService Provider Appointment Slot`
		WHERE shift_assignment = %s
		AND (service_appointment IS NULL OR service_appointment = '')
		AND posting_date IN %s
	""",
		(shift_assignment, dates_to_delete),
	)

	frappe.db.commit()

	count = deleted_count if isinstance(deleted_count, int) else len(dates_to_delete)
	return f"Deleted slots for {', '.join(weekdays)} ({count} dates processed)"


def service_type_requires_service_unit(service_type):
	"""
	Check if a service type requires a service unit
	Returns: (requires_unit: bool, unit_types: list)
	"""
	apt_type = frappe.get_doc("Service Type", service_type)

	if not apt_type.service_unit_types or len(apt_type.service_unit_types) == 0:
		return False, []

	unit_types = [row.service_unit_type for row in apt_type.service_unit_types]
	return True, unit_types


@frappe.whitelist()
def get_available_slots(appointment_type, provider=None, date=None, days_ahead=30):
	"""
	Get available slots for an appointment type

	Args:
		appointment_type: Name of the Appointment Type
		provider: Optional - Filter by specific provider
		date: Optional - Filter by specific date (YYYY-MM-DD)
		days_ahead: Number of days to look ahead if no date specified

	Returns:
		List of available slots grouped by provider and date
	"""

	apt_type = frappe.db.get_value(
		"Service Type",
		appointment_type,
		["default_duration_in_minutes", "buffer_before", "buffer_after"],
		as_dict=True,
	)
	duration = apt_type.default_duration_in_minutes

	# Check if service unit is required
	requires_unit, required_unit_types = service_type_requires_service_unit(appointment_type)

	settings = frappe.get_single("Service Appointment Settings")
	buffer_before = apt_type.buffer_before or settings.buffer_before or 0
	buffer_after = apt_type.buffer_after or settings.buffer_after or 0
	allow_past_booking = settings.allow_past_booking

	if provider:
		can_provide = frappe.db.exists(
			"Service Provider Service", {"parent": provider, "service_type": appointment_type, "disabled": 0}
		)
		if not can_provide:
			frappe.throw(_("Provider {0} cannot provide service type {1}").format(provider, appointment_type))
		providers = [provider]
	else:
		providers = frappe.db.sql(
			"""
			SELECT DISTINCT sps.parent
			FROM `tabService Provider Service` sps
			INNER JOIN `tabService Provider` p ON sps.parent = p.name
			WHERE sps.service_type = %s
			AND sps.disabled = 0
			AND p.active = 1
		""",
			appointment_type,
			pluck="parent",
		)

	if not providers:
		return []

	if date:
		start_date = getdate(date)
		end_date = start_date
	else:
		start_date = getdate(nowdate())
		days_ahead = settings.max_advance_days or days_ahead
		end_date = add_days(start_date, days_ahead)

	past_booking_filter = ""
	if not allow_past_booking:
		past_booking_filter = """
		AND (
			s.posting_date > CURDATE()
			OR (s.posting_date = CURDATE() AND s.start_time > CURTIME())
		)
	"""

	if requires_unit:
		slots = frappe.db.sql(
			f"""
			SELECT
				s.name,
				s.provider,
				p.provider_name,
				s.service_unit,
				su.unit_name,
				su.unit_type,
				su.capacity,
				s.posting_date,
				s.start_time,
				s.end_time,
				s.shift_assignment,
				TIMEDIFF(s.end_time, s.start_time) as slot_duration_minutes
			FROM `tabService Provider Appointment Slot` s
			INNER JOIN `tabService Provider` p ON s.provider = p.name
			INNER JOIN `tabService Unit` su ON s.service_unit = su.name
			WHERE s.provider IN %(providers)s
			AND s.posting_date BETWEEN %(start_date)s AND %(end_date)s
			AND s.is_available = 1
			AND (s.service_appointment IS NULL OR s.service_appointment = '')
			AND p.active = 1
			AND su.unit_type IN %(required_unit_types)s
			AND su.disabled = 0
			AND su.allow_appointments = 1
			{past_booking_filter}
			ORDER BY s.posting_date, s.start_time, p.provider_name, su.unit_name
		""",
			{
				"providers": providers,
				"start_date": start_date,
				"end_date": end_date,
				"required_unit_types": required_unit_types,
			},
			as_dict=True,
		)

	else:
		slots = frappe.db.sql(
			f"""
			SELECT
				s.name,
				s.provider,
				p.provider_name,
				NULL as service_unit,
				NULL as unit_name,
				NULL as unit_type,
				NULL as capacity,
				s.posting_date,
				s.start_time,
				s.end_time,
				s.shift_assignment,
				TIMEDIFF(s.end_time, s.start_time) as slot_duration_minutes
			FROM `tabService Provider Appointment Slot` s
			INNER JOIN `tabService Provider` p ON s.provider = p.name
			WHERE s.provider IN %(providers)s
			AND s.posting_date BETWEEN %(start_date)s AND %(end_date)s
			AND s.is_available = 1
			AND (s.service_appointment IS NULL OR s.service_appointment = '')
			AND p.active = 1
			{past_booking_filter}
			ORDER BY s.posting_date, s.start_time, p.provider_name
		""",
			{"providers": providers, "start_date": start_date, "end_date": end_date},
			as_dict=True,
		)

	available_slots = group_slots_by_duration_and_capacity(
		slots, duration, buffer_before, buffer_after, appointment_type, requires_unit
	)

	return format_available_slots(available_slots)


def group_slots_by_duration_and_capacity(
	slots, required_duration, buffer_before, buffer_after, appointment_type, requires_unit
):
	"""
	Group consecutive slots that can accommodate the required duration plus buffers and capacity constraints

	Args:
		slots: List of slot dictionaries
		required_duration: Required duration in minutes
		buffer_before: Buffer time before appointment in minutes
		buffer_after: Buffer time after appointment in minutes
		appointment_type: Service being rendered
		requires_unit: Does service require a physical/logical resource


	Returns:
		List of available time slots with their component slots
	"""

	available_slots = []
	total_duration_needed = required_duration + buffer_before + buffer_after

	apt_type = frappe.db.get_value("Service Type", appointment_type, ["max_clients_per_slot"], as_dict=True)
	max_clients = apt_type.max_clients_per_slot or 1

	# Group by provider and date
	grouped = {}
	for slot in slots:
		if requires_unit:
			key = (slot.provider, slot.posting_date, slot.service_unit)
		else:
			key = (slot.provider, slot.posting_date)

		if key not in grouped:
			grouped[key] = []
		grouped[key].append(slot)

	# For each provider-date combination, find consecutive slots
	for key, day_slots in grouped.items():
		if requires_unit:
			provider, date, service_unit = key
		else:
			provider, date = key
			service_unit = None

		i = 0
		while i < len(day_slots):
			current_slot = day_slots[i]
			start_time_raw = current_slot.start_time
			if isinstance(start_time_raw, timedelta):
				start_time = (datetime.min + start_time_raw).time()
			else:
				start_time = start_time_raw

			accumulated_minutes = 0
			component_slots = []

			# Try to accumulate consecutive slots
			j = i
			while j < len(day_slots):
				slot = day_slots[j]

				# Check if this slot is consecutive with the previous
				if component_slots:
					last_slot = component_slots[-1]
					if isinstance(last_slot.end_time, timedelta):
						last_slot_end_time = (datetime.min + last_slot.end_time).time()
					else:
						last_slot_end_time = last_slot.end_time

					last_end_dt = datetime.combine(datetime.today(), last_slot_end_time)

					if isinstance(slot.start_time, timedelta):
						current_slot_start_time = (datetime.min + slot.start_time).time()
					else:
						current_slot_start_time = slot.start_time

					current_start_dt = datetime.combine(datetime.today(), current_slot_start_time)
					gap = current_start_dt - last_end_dt

					# Ensure no gaps > 1 minute or overlaps
					if gap > timedelta(minutes=1) or gap < timedelta(seconds=-1):
						break

				component_slots.append(slot)

				slot_duration_timedelta = slot.slot_duration_minutes
				slot_duration = int(slot_duration_timedelta.total_seconds() / 60)
				accumulated_minutes += slot_duration

				# If we have enough duration, create an available slot
				if accumulated_minutes >= total_duration_needed:
					actual_start_time = get_end_time_for_duration(start_time, buffer_before)
					actual_end_time = get_end_time_for_duration(actual_start_time, required_duration)

					if requires_unit:
						capacity_available = check_service_unit_capacity(
							service_unit,
							date,
							actual_start_time,
							actual_end_time,
							appointment_type,
							max_clients,
						)

						if not capacity_available:
							break

					else:
						capacity_available = check_provider_slot_capacity(
							provider, date, actual_start_time, actual_end_time, max_clients
						)

						if not capacity_available:
							break

					available_slots.append(
						{
							"provider": provider,
							"provider_name": current_slot.provider_name,
							"service_unit": service_unit,
							"service_unit_name": getattr(current_slot, "unit_name", None),
							"date": date,
							"start_time": actual_start_time,
							"end_time": actual_end_time,
							"duration": required_duration,
							"buffer_before": buffer_before,
							"buffer_after": buffer_after,
							"slot_ids": [s.name for s in component_slots],
							"shift_assignment": current_slot.shift_assignment,
						}
					)
					break

				j += 1

			i += 1

	return available_slots


def check_service_unit_capacity(
	service_unit, date, start_time, end_time, appointment_type, max_clients_per_slot, exclude_appointment=None
):
	"""
	Check if service unit has capacity for this time slot

	Logic:
	1. Get service unit capacity (default from Service Unit if not specified in Service Type)
	2. Check how many appointments already exist for this time slot
	3. Account for overlapping appointments if allow_overlap is true
	4. Return True if capacity is available
	"""

	service_unit_doc = frappe.get_doc("Service Unit", service_unit)

	# Determine effective capacity
	# Priority: Service Type > Service Unit
	apt_type = frappe.get_doc("Service Type", appointment_type)
	capacity = None

	# Check if capacity is specified in Service Type's service_unit_types
	for row in apt_type.service_unit_types:
		if row.service_unit_type == service_unit_doc.unit_type:
			if row.capacity:
				capacity = row.capacity
			break

	# Fallback to Service Unit's capacity
	if capacity is None:
		capacity = service_unit_doc.capacity or 1

	# If allow_overlap is true, capacity can be higher
	if service_unit_doc.allow_overlap:
		# Use max_clients_per_slot if specified, otherwise use capacity
		effective_capacity = max(capacity, max_clients_per_slot)
	else:
		effective_capacity = min(capacity, max_clients_per_slot)

	filters = {
		"service_unit": service_unit,
		"appointment_date": date,
		"status": ["not in", ["Cancelled", "No Show"]],
		"docstatus": ["!=", 2],  # Not cancelled
		# Check for time overlap
		"start_time": ["<=", end_time],
		"end_time": [">=", start_time],
	}

	if exclude_appointment:
		filters["name"] = ["!=", exclude_appointment]

	# Count existing appointments in this time slot
	existing_count = frappe.db.count("Service Appointment", filters)

	return existing_count < effective_capacity


def check_provider_slot_capacity(
	provider, date, start_time, end_time, max_clients_per_slot, exclude_appointment=None
):
	"""
	Check provider capacity for services that don't require service units
	Uses max_clients_per_slot from Service Type
	"""
	# Count existing appointments for this provider in this time slot
	# regardless of service unit
	filters = {
		"appointment_provider": provider,
		"appointment_date": date,
		"status": ["not in", ["Cancelled", "No Show"]],
		"docstatus": ["!=", 2],
		# Check for time overlap
		"start_time": ["<", end_time],
		"end_time": [">", start_time],
	}

	if exclude_appointment:
		filters["name"] = ["!=", exclude_appointment]

	existing_count = frappe.db.count("Service Appointment", filters)

	return existing_count < max_clients_per_slot


def get_end_time_for_duration(start_time, duration_minutes):
	"""Calculate end time given start time and duration"""

	if isinstance(start_time, str):
		start_time = datetime.strptime(start_time, "%H:%M:%S").time()

	start_dt = datetime.combine(datetime.today(), start_time)
	end_dt = start_dt + timedelta(minutes=duration_minutes)

	return end_dt.time()


def format_available_slots(slots):
	"""Format slots for frontend consumption"""
	# Group by provider
	by_provider = {}
	for slot in slots:
		provider = slot["provider"]
		if provider not in by_provider:
			by_provider[provider] = {
				"provider": provider,
				"provider_name": slot["provider_name"],
				"dates": {},
			}

		date = str(slot["date"])
		if date not in by_provider[provider]["dates"]:
			by_provider[provider]["dates"][date] = []

		by_provider[provider]["dates"][date].append(
			{
				"start_time": str(slot["start_time"]),
				"end_time": str(slot["end_time"]),
				"duration": slot["duration"],
				"buffer_before": slot.get("buffer_before", 0),
				"buffer_after": slot.get("buffer_after", 0),
				"slot_ids": slot["slot_ids"],
				"shift_assignment": slot["shift_assignment"],
			}
		)

	# Convert to list
	result = []
	for provider_data in by_provider.values():
		# Convert dates dict to sorted list
		dates_list = []
		for date, times in sorted(provider_data["dates"].items()):
			dates_list.append({"date": date, "slots": times})

		result.append(
			{
				"provider": provider_data["provider"],
				"provider_name": provider_data["provider_name"],
				"available_dates": dates_list,
			}
		)

	return result


@frappe.whitelist()
def book_appointment_slot(appointment, provider, date, start_time, slot_ids):
	"""
	Book slots for an appointment

	Args:
		appointment: Service Appointment name
		provider: Provider ID
		date: Appointment date
		start_time: Start time
		slot_ids: JSON array of slot IDs to book
	"""
	import json

	if isinstance(slot_ids, str):
		slot_ids = json.loads(slot_ids)

	# Validate all slots are still available
	for slot_id in slot_ids:
		slot = frappe.get_doc("Service Provider Appointment Slot", slot_id)

		if not slot.is_available or slot.service_appointment:
			frappe.throw(
				_("Slot {0} is no longer available. Please select another time.").format(slot_id),
				title=_("Slot Not Available"),
			)

	# Book all slots
	for slot_id in slot_ids:
		frappe.db.set_value(
			"Service Provider Appointment Slot",
			slot_id,
			{"service_appointment": appointment, "is_available": 0},
		)

	frappe.db.commit()

	return {
		"success": True,
		"message": _("Appointment slots booked successfully"),
		"slots_booked": len(slot_ids),
	}


@frappe.whitelist()
def release_appointment_slots(appointment):
	"""
	Release slots when appointment is cancelled

	Args:
		appointment: Service Appointment name
	"""
	frappe.db.sql(
		"""
		UPDATE `tabService Provider Appointment Slot`
		SET service_appointment = NULL,
			is_available = 1
		WHERE service_appointment = %s
	""",
		appointment,
	)

	frappe.db.commit()

	return {"success": True, "message": _("Appointment slots released")}
