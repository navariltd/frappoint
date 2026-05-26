# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

import json
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	add_days,
	get_time,
	getdate,
	nowdate,
)


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


def _parse_slot_ids(slot_ids):
	if not slot_ids:
		return []

	if isinstance(slot_ids, str):
		return json.loads(slot_ids)

	return list(slot_ids)


def _get_current_booked_slot_ids(appointment_name):
	return frappe.get_all(
		"Service Provider Appointment Slot",
		filters={"service_appointment": appointment_name},
		pluck="name",
		order_by="start_time asc, name asc",
	)


def _get_provider_change_options(appointment):
	available_slots = get_available_slots(
		appointment.appointment_type,
		appointment.duration,
		date=appointment.appointment_date,
	)

	for date_group in available_slots:
		if str(date_group.get("date")) != str(appointment.appointment_date):
			continue

		for time_slot in date_group.get("slots", []):
			if str(time_slot.get("start_time")) != str(appointment.start_time):
				continue

			if str(time_slot.get("end_time")) != str(appointment.end_time):
				continue

			return [
				provider
				for provider in time_slot.get("providers", [])
				if provider.get("provider") != appointment.appointment_provider
			]

	return []


def _validate_replacement_slots(appointment, slot_ids):
	replacement_slots = []
	provider_name = None

	for slot_id in slot_ids:
		slot = frappe.get_doc("Service Provider Appointment Slot", slot_id)

		if not slot.is_available or slot.service_appointment:
			frappe.throw(
				_("Slot {0} is no longer available. Please select another provider.").format(slot_id),
				title=_("Slot Not Available"),
			)

		if str(slot.posting_date) != str(appointment.appointment_date):
			frappe.throw(_("Selected slot {0} does not match the appointment date.").format(slot_id))

		if str(slot.start_time) < str(appointment.start_time) or str(slot.end_time) > str(
			appointment.end_time
		):
			frappe.throw(_("Selected slot {0} does not match the appointment time window.").format(slot_id))

		if provider_name is None:
			provider_name = slot.provider
		elif provider_name != slot.provider:
			frappe.throw(_("All selected slots must belong to the same provider."))

		replacement_slots.append(slot)

	return provider_name, replacement_slots


def _apply_provider_change(appointment, slot_ids):
	current_slot_ids = _get_current_booked_slot_ids(appointment.name)
	if not current_slot_ids:
		frappe.throw(_("No booked slots were found for this appointment."))

	if len(current_slot_ids) != len(slot_ids):
		frappe.throw(
			_("The selected provider must have the same number of slots as the current appointment.")
		)

	provider_name, replacement_slots = _validate_replacement_slots(appointment, slot_ids)

	release_appointment_slots(appointment.name, commit=False)

	appointment.selected_slot_ids = json.dumps(slot_ids)
	appointment.appointment_provider = provider_name
	appointment.service_unit = replacement_slots[0].service_unit if replacement_slots else None
	appointment.book_selected_slots()

	provider_label = frappe.db.get_value("Service Provider", provider_name, "provider_name")
	frappe.db.set_value(
		"Service Appointment",
		appointment.name,
		{
			"selected_slot_ids": json.dumps(slot_ids),
			"appointment_provider": provider_name,
			"service_unit": appointment.service_unit,
			"service_provider_name": provider_label,
		},
	)

	return {
		"provider": provider_name,
		"provider_name": provider_label,
		"slot_ids": slot_ids,
	}


@frappe.whitelist()
def change_appointment_provider(appointment_name, slot_ids=None):
	appointment = frappe.get_doc("Service Appointment", appointment_name)
	current_slot_ids = _get_current_booked_slot_ids(appointment.name)

	if appointment.docstatus == 2 or appointment.status in [
		"Cancelled",
		"Closed",
		"Completed",
		"No Show",
	]:
		frappe.throw(_("This appointment cannot be changed."))

	if not current_slot_ids and not slot_ids:
		return {
			"success": True,
			"appointment": appointment.name,
			"current_provider": appointment.appointment_provider,
			"provider_change_options": [],
		}

	provider_options = _get_provider_change_options(appointment)

	if not slot_ids:
		return {
			"success": True,
			"appointment": appointment.name,
			"current_provider": appointment.appointment_provider,
			"provider_change_options": provider_options,
		}

	slot_ids = _parse_slot_ids(slot_ids)
	if not slot_ids:
		frappe.throw(_("At least one replacement slot must be selected."))

	selected_option = None
	for provider in provider_options:
		if provider.get("slot_ids") == slot_ids:
			selected_option = provider
			break

	if not selected_option:
		frappe.throw(_("The selected slot combination is no longer available."))

	if selected_option is not None and selected_option.get("provider") == appointment.appointment_provider:
		return {
			"success": True,
			"appointment": appointment.name,
			"current_provider": appointment.appointment_provider,
			"provider_change_options": provider_options,
		}

	change_result = _apply_provider_change(appointment, slot_ids)
	frappe.db.commit()

	return {
		"success": True,
		"message": _("Appointment provider changed successfully."),
		"appointment": appointment.name,
		"current_provider": change_result.get("provider"),
		"provider_name": change_result.get("provider_name"),
		"slot_ids": change_result.get("slot_ids"),
		"provider_change_options": provider_options,
	}


def insert_slot(provider, slot_date, start_time, end_time, shift_assignment):
	exists = frappe.db.exists(
		"Service Provider Appointment Slot",
		{
			"provider": provider,
			"posting_date": slot_date,
			"start_time": start_time,
			"end_time": end_time,
		},
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
	from ...services.slot_cache_service import invalidate_provider_date_range_cache

	sa = frappe.get_doc("Service Provider Shift Assignment", shift_assignment)
	st = frappe.get_doc("Service Provider Shift Type", sa.shift_type)

	if sa.status == "Inactive":
		frappe.db.set_value(
			"Service Provider Appointment Slot",
			{"shift_assignment": shift_assignment},
			"is_available",
			0,
		)
		frappe.db.commit()
		invalidate_provider_date_range_cache(
			sa.provider, sa.start_date, sa.end_date or add_days(nowdate(), 365)
		)
		return "Slots marked as unavailable"

	frappe.db.delete(
		"Service Provider Appointment Slot",
		{
			"shift_assignment": shift_assignment,
			"service_appointment": ["is", "not set"],
		},
	)
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
			filters={
				"parent": holiday_list,
				"holiday_date": ["between", [start_date, end_date]],
			},
			pluck="holiday_date",
		)
		holidays = set(holiday_records)

	# allowed weekdays for weekly repeat
	allowed_weekdays = set()
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

			exists = frappe.db.exists(
				"Service Provider Appointment Slot",
				{
					"provider": provider,
					"posting_date": dt,
					"start_time": start_t,
					"end_time": end_t,
					"service_unit": sa.service_unit,
				},
			)

			if not exists:
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

	invalidate_provider_date_range_cache(sa.provider, start_date, end_date)

	return f"Slots generated: {len(slots_to_insert)}"


def generate_slots_for_specific_days(shift_assignment, weekdays, start_date, end_date):
	"""Generate slots only for specific weekdays"""
	from ...services.slot_cache_service import invalidate_provider_date_range_cache

	sa = frappe.get_doc("Service Provider Shift Assignment", shift_assignment)
	st = frappe.get_doc("Service Provider Shift Type", sa.shift_type)

	if sa.status == "Inactive":
		return

	provider = sa.provider
	slot_size = get_global_slot_size()
	holiday_list = st.holiday_list
	max_advance_days = get_global_max_advance_days()

	if end_date is None:
		end_date = start_date + timedelta(days=max_advance_days)

	# Map weekday names to indices
	weekday_indices = {DAYS.index(day) for day in weekdays}

	# Batch fetch holidays once
	holidays = set()
	if holiday_list:
		holiday_records = frappe.db.get_all(
			"Holiday",
			filters={
				"parent": holiday_list,
				"holiday_date": ["between", [start_date, end_date]],
			},
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
				{
					"provider": provider,
					"posting_date": dt,
					"start_time": start_t,
					"end_time": end_t,
				},
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

	invalidate_provider_date_range_cache(sa.provider, start_date, end_date)

	return f"Generated {len(slots_to_insert)} new slots for {', '.join(weekdays)}"


def delete_slots_for_specific_days(shift_assignment, weekdays):
	"""Delete slots only for specific weekdays (only unbooked slots)"""
	from ...services.slot_cache_service import invalidate_provider_date_range_cache

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
	invalidate_provider_date_range_cache(sa.provider, start_date, end_date)

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
def get_available_slots(appointment_type, duration, provider=None, date=None, gender=None, days_ahead=30):
	from ...services.slot_cache_service import get_cached_available_slots

	def _compute_for_day(day_date):
		return _get_available_slots_db(
			appointment_type=appointment_type,
			duration=duration,
			provider=None,
			date=day_date,
			gender=None,
			days_ahead=0,
		)

	try:
		return get_cached_available_slots(
			appointment_type=appointment_type,
			duration=duration,
			provider=provider,
			date=date,
			gender=gender,
			days_ahead=days_ahead,
			compute_day_fn=_compute_for_day,
		)
	except Exception:
		# Fallback to DB path on cache layer failures.
		return _get_available_slots_db(
			appointment_type=appointment_type,
			duration=duration,
			provider=provider,
			date=date,
			gender=gender,
			days_ahead=days_ahead,
		)


def _get_available_slots_db(appointment_type, duration, provider=None, date=None, gender=None, days_ahead=30):
	"""
	Get available slots for an appointment type

	Args:
			appointment_type: Name of the Appointment Type
			duration: Duration of the appointment
			provider: Optional - Filter by specific provider
			date: Optional - Filter by specific date (YYYY-MM-DD)
			gender: Optional - Filter providers by gender
			days_ahead: Number of days to look ahead if no date specified

	Returns:
			List of available slots grouped by provider and date
	"""

	apt_type = frappe.db.get_value(
		"Service Type",
		appointment_type,
		["buffer_before", "buffer_after"],
		as_dict=True,
	)
	duration = int(duration)

	# Check if service unit is required
	requires_unit, required_unit_types = service_type_requires_service_unit(appointment_type)

	settings = frappe.get_single("Service Appointment Settings")
	buffer_before = apt_type.buffer_before or settings.buffer_before or 0
	buffer_after = apt_type.buffer_after or settings.buffer_after or 0
	allow_past_booking = settings.allow_past_booking

	if provider:
		can_provide = frappe.db.exists(
			"Service Provider Service",
			{"parent": provider, "service_type": appointment_type, "disabled": 0},
		)
		if not can_provide:
			frappe.throw(_("Provider {0} cannot provide service type {1}").format(provider, appointment_type))
		providers = [provider]
	else:
		# Build the query to fetch providers
		gender_filter = ""
		if gender:
			gender_filter = f" AND p.gender = {frappe.db.escape(gender)}"

		providers = frappe.db.sql(
			f"""
			SELECT DISTINCT sps.parent
			FROM `tabService Provider Service` sps
			INNER JOIN `tabService Provider` p ON sps.parent = p.name
			WHERE sps.service_type = %s
			AND sps.disabled = 0
			AND p.active = 1
			{gender_filter}
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
			AND s.service_unit IS NULL
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
	slots,
	required_duration,
	buffer_before,
	buffer_after,
	appointment_type,
	requires_unit,
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
					customer_start_time = get_end_time_for_duration(start_time, buffer_before)
					customer_end_time = get_end_time_for_duration(customer_start_time, required_duration)

					reserved_start_time = start_time
					reserved_end_time = get_end_time_for_duration(customer_end_time, buffer_after)

					if requires_unit:
						capacity_available = check_service_unit_capacity(
							service_unit,
							date,
							reserved_start_time,
							reserved_end_time,
							appointment_type,
							max_clients,
						)

						if not capacity_available:
							break

						provider_available = check_provider_slot_capacity(
							provider,
							date,
							reserved_start_time,
							reserved_end_time,
							max_clients,
						)

						if not provider_available:
							break

					else:
						capacity_available = check_provider_slot_capacity(
							provider,
							date,
							reserved_start_time,
							reserved_end_time,
							max_clients,
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
							"start_time": customer_start_time,
							"end_time": customer_end_time,
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
	service_unit,
	date,
	start_time,
	end_time,
	appointment_type,
	max_clients_per_slot,
	exclude_appointment=None,
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

	# If overlap is disabled, enforce single occupancy regardless of configured capacities.
	if service_unit_doc.allow_overlap:
		# Use max_clients_per_slot if specified, otherwise use capacity
		effective_capacity = max(capacity, max_clients_per_slot)
	else:
		effective_capacity = 1

	filters = {
		"service_unit": service_unit,
		"appointment_date": date,
		"status": ["not in", ["Cancelled", "No Show", "Closed"]],
		"docstatus": ["!=", 2],  # Not cancelled
		# Half-open interval overlap: existing.start < new.end AND existing.end > new.start
		"start_time": ["<", end_time],
		"end_time": [">", start_time],
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
		"status": ["not in", ["Cancelled", "No Show", "Closed"]],
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
	# # Group by provider
	# by_provider = {}
	# for slot in slots:
	# 	provider = slot["provider"]
	# 	if provider not in by_provider:
	# 		by_provider[provider] = {
	# 			"provider": provider,
	# 			"provider_name": slot["provider_name"],
	# 			"dates": {},
	# 		}

	# 	date = str(slot["date"])
	# 	if date not in by_provider[provider]["dates"]:
	# 		by_provider[provider]["dates"][date] = []

	# 	by_provider[provider]["dates"][date].append(
	# 		{
	# 			"start_time": str(slot["start_time"]),
	# 			"end_time": str(slot["end_time"]),
	# 			"duration": slot["duration"],
	# 			"buffer_before": slot.get("buffer_before", 0),
	# 			"buffer_after": slot.get("buffer_after", 0),
	# 			"slot_ids": slot["slot_ids"],
	# 			"shift_assignment": slot["shift_assignment"],
	# 		}
	# 	)

	# # Convert to list
	# result = []
	# for provider_data in by_provider.values():
	# 	# Convert dates dict to sorted list
	# 	dates_list = []
	# 	for date, times in sorted(provider_data["dates"].items()):
	# 		dates_list.append({"date": date, "slots": times})

	# 	result.append(
	# 		{
	# 			"provider": provider_data["provider"],
	# 			"provider_name": provider_data["provider_name"],
	# 			"available_dates": dates_list,
	# 		}
	# 	)

	# Group by date
	by_date = {}

	for slot in slots:
		date_str = str(slot["date"])
		time_key = f"{slot['start_time']}-{slot['end_time']}"

		if date_str not in by_date:
			by_date[date_str] = {}

		if time_key not in by_date[date_str]:
			by_date[date_str][time_key] = {
				"start_time": str(slot["start_time"]),
				"end_time": str(slot["end_time"]),
				"duration": slot["duration"],
				"buffer_before": slot.get("buffer_before", 0),
				"buffer_after": slot.get("buffer_after", 0),
				"providers": [],
			}

		by_date[date_str][time_key]["providers"].append(
			{
				"provider": slot["provider"],
				"provider_name": slot["provider_name"],
				"service_unit": slot.get("service_unit"),
				"service_unit_name": slot.get("service_unit_name"),
				"slot_ids": slot["slot_ids"],
				"shift_assignment": slot.get("shift_assignment"),
			}
		)

	formatted_result = []
	for date in sorted(by_date.keys()):
		time_slots = sorted(by_date[date].values(), key=lambda x: x["start_time"])
		formatted_result.append({"date": date, "slots": time_slots})

	return formatted_result


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

	if isinstance(slot_ids, str):
		slot_ids = json.loads(slot_ids)

	reserve_slots_atomically(appointment=appointment, slot_ids=slot_ids)

	frappe.db.commit()

	return {
		"success": True,
		"message": _("Appointment slots booked successfully"),
		"slots_booked": len(slot_ids),
	}


def reserve_slots_atomically(appointment, slot_ids):
	"""
	Concurrency-safe reservation using row-level locks.
	DB locking is the source of truth; cache is updated by invalidation after write paths.
	"""
	if not slot_ids:
		return

	if isinstance(slot_ids, str):
		slot_ids = json.loads(slot_ids)

	slot_ids = list(dict.fromkeys(slot_ids))
	if not slot_ids:
		return

	locked_rows = frappe.db.sql(
		"""
		SELECT name
		FROM `tabService Provider Appointment Slot`
		WHERE name IN %(slot_ids)s
		AND is_available = 1
		AND (service_appointment IS NULL OR service_appointment = '')
		FOR UPDATE
	""",
		{"slot_ids": tuple(slot_ids)},
		as_dict=True,
	)

	if len(locked_rows) != len(slot_ids):
		frappe.throw(
			_("One or more slots are no longer available. Please select another time."),
			title=_("Slot Not Available"),
		)

	frappe.db.sql(
		"""
		UPDATE `tabService Provider Appointment Slot`
		SET service_appointment = %(appointment)s,
			is_available = 0
		WHERE name IN %(slot_ids)s
	""",
		{"appointment": appointment, "slot_ids": tuple(slot_ids)},
	)


@frappe.whitelist()
def release_appointment_slots(appointment, commit=True):
	"""
	Release slots when appointment is cancelled

	Args:
									appointment: Service Appointment name
	"""
	appointment_meta = frappe.db.get_value(
		"Service Appointment",
		appointment,
		["appointment_type", "appointment_date"],
		as_dict=True,
	)

	frappe.db.sql(
		"""
		UPDATE `tabService Provider Appointment Slot`
		SET service_appointment = NULL,
			is_available = 1
		WHERE service_appointment = %s
	""",
		appointment,
	)

	# Commit BEFORE cache operations so any warm job that runs on a separate
	# DB connection already sees the released (available) slot state.
	if commit:
		frappe.db.commit()

	if (
		commit
		and appointment_meta
		and appointment_meta.appointment_type
		and appointment_meta.appointment_date
	):
		from ...services.slot_cache_service import invalidate_service_date_cache, queue_warm_service_date

		invalidate_service_date_cache(
			appointment_meta.appointment_type,
			appointment_meta.appointment_date,
		)
		queue_warm_service_date(
			appointment_meta.appointment_type,
			appointment_meta.appointment_date,
		)

	return {"success": True, "message": _("Appointment slots released")}
