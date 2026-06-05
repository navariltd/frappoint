from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta
from math import ceil
from typing import Any

import frappe
from frappe.utils import add_days, cint, flt, get_time, getdate, nowdate

ACTIVE_ALLOCATION_STATUSES = ("Draft", "Held", "Confirmed")
WEEKDAY_FIELD_MAP = {
	0: "monday",
	1: "tuesday",
	2: "wednesday",
	3: "thursday",
	4: "friday",
	5: "saturday",
	6: "sunday",
}


def rebuild_counter_for_date(
	counter_date,
	resource_type: str | None = None,
	resource_reference: str | None = None,
) -> dict[str, int]:
	"""Rebuild availability counters for a specific date, optionally filtered by resource."""
	target_date = getdate(counter_date)
	slot_size = _get_slot_size_minutes()

	base_slots = _build_shift_capacity_slots(
		target_date,
		slot_size,
		resource_type=resource_type,
		resource_reference=resource_reference,
	)
	consumption = _build_consumption_map(
		target_date,
		slot_size,
		resource_type=resource_type,
		resource_reference=resource_reference,
	)

	_delete_existing_counters(target_date, resource_type, resource_reference)

	inserted = 0
	for key, base in base_slots.items():
		r_type, r_ref, slot_time = key
		max_capacity = flt(base["max_capacity"])
		consumed = min(max_capacity, flt(consumption.get(key, 0.0)))

		doc = frappe.get_doc(
			{
				"doctype": "Resource Availability Counter",
				"counter_date": target_date,
				"counter_slot_time": slot_time,
				"resource_type": r_type,
				"resource_reference": r_ref,
				"slot_duration_minutes": slot_size,
				"max_capacity": max_capacity,
				"consumed_capacity": consumed,
				"is_blocked": 1 if base.get("is_blocked") else 0,
				"block_reason": base.get("block_reason"),
				"source_type": base.get("source_type") or "Shift",
				"source_reference": base.get("source_reference"),
			}
		)
		doc.insert(ignore_permissions=True)
		inserted += 1

	return {"date": str(target_date), "inserted": inserted, "slot_size_minutes": slot_size}


def rebuild_counters_range(
	start_date,
	end_date,
	resource_type: str | None = None,
	resource_reference: str | None = None,
) -> dict[str, Any]:
	"""Rebuild availability counters for a date range inclusive."""
	start = getdate(start_date)
	end = getdate(end_date)

	if end < start:
		start, end = end, start

	results = []
	current = start
	while current <= end:
		results.append(
			rebuild_counter_for_date(
				counter_date=current,
				resource_type=resource_type,
				resource_reference=resource_reference,
			)
		)
		current = add_days(current, 1)

	return {
		"start_date": str(start),
		"end_date": str(end),
		"days": len(results),
		"results": results,
	}


def invalidate_counter(counter_date, resource_type: str, resource_reference: str) -> None:
	"""Invalidate counter rows for a specific resource/date.

	We invalidate by deleting rows, allowing lazy rebuild on next access.
	"""
	frappe.db.delete(
		"Resource Availability Counter",
		{
			"counter_date": getdate(counter_date),
			"resource_type": resource_type,
			"resource_reference": resource_reference,
		},
	)


def get_available_slots(
	service_type_id: str,
	start_date,
	end_date,
	provider_id: str | None = None,
	service_unit_id: str | None = None,
	required_duration_minutes: int | None = None,
	exclude_appointment_id: str | None = None,
) -> list[dict[str, Any]]:
	"""Return availability windows using precomputed counter rows only."""
	del exclude_appointment_id

	if not _counter_table_ready():
		frappe.throw(
			"Availability counters are not initialized for this site. Run bench migrate for this site."
		)

	start = getdate(start_date)
	end = getdate(end_date)
	if end < start:
		start, end = end, start

	service_type = frappe.db.get_value(
		"Service Type",
		service_type_id,
		["default_duration_in_minutes", "buffer_before", "buffer_after"],
		as_dict=True,
	)
	if not service_type:
		return []

	duration = cint(required_duration_minutes or service_type.default_duration_in_minutes or 0)
	buffer_before = cint(service_type.buffer_before or 0)
	buffer_after = cint(service_type.buffer_after or 0)
	if duration <= 0:
		return []

	slot_size = _get_slot_size_minutes()
	total_needed = duration + buffer_before + buffer_after
	slots_needed = ceil(total_needed / slot_size)

	provider_ids = _get_service_providers(service_type_id, provider_id)
	if not provider_ids:
		return []

	requires_unit, unit_types = _service_type_requires_unit(service_type_id)
	unit_filters: dict[str, Any] = {}
	if requires_unit:
		if service_unit_id:
			unit_filters["name"] = service_unit_id
		elif unit_types:
			unit_filters["unit_type"] = ["in", unit_types]
		unit_filters["disabled"] = 0
		unit_filters["allow_appointments"] = 1

	provider_names = {
		row["name"]: row["provider_name"]
		for row in frappe.get_all(
			"Service Provider",
			filters={"name": ["in", provider_ids]},
			fields=["name", "provider_name"],
		)
	}

	provider_counters = frappe.get_all(
		"Resource Availability Counter",
		filters={
			"resource_type": "Service Provider",
			"resource_reference": ["in", provider_ids],
			"counter_date": ["between", [start, end]],
		},
		fields=[
			"counter_date",
			"counter_slot_time",
			"resource_reference",
			"remaining_capacity",
			"is_blocked",
		],
	)

	unit_counters: list[dict[str, Any]] = []
	unit_names: dict[str, str] = {}
	provider_unit_shift_map: dict[str, dict[Any, dict[str, set[time]]]] = {}
	if requires_unit:
		units = frappe.get_all("Service Unit", filters=unit_filters, fields=["name", "unit_name"])
		unit_ids = [row["name"] for row in units]
		unit_names = {row["name"]: row["unit_name"] for row in units}
		if not unit_ids:
			return []

		provider_unit_shift_map = _build_provider_unit_shift_map(
			start=start,
			end=end,
			provider_ids=provider_ids,
			allowed_unit_ids=set(unit_ids),
			slot_size_minutes=slot_size,
		)

		unit_counters = frappe.get_all(
			"Resource Availability Counter",
			filters={
				"resource_type": "Service Unit",
				"resource_reference": ["in", unit_ids],
				"counter_date": ["between", [start, end]],
			},
			fields=[
				"counter_date",
				"counter_slot_time",
				"resource_reference",
				"remaining_capacity",
				"is_blocked",
			],
		)

	provider_slot_map = _build_available_slot_map(provider_counters)
	unit_slot_map = _build_available_slot_map(unit_counters) if requires_unit else {}

	results: list[dict[str, Any]] = []
	for provider in provider_ids:
		for date_key, slot_times in provider_slot_map.get(provider, {}).items():
			windows = _find_contiguous_windows(slot_times, slot_size, slots_needed)
			for start_slot in windows:
				unit_id = None
				unit_name = None
				if requires_unit:
					candidate_unit_ids = _get_provider_window_candidate_units(
						provider_unit_shift_map,
						provider,
						date_key,
						start_slot,
						slots_needed,
						slot_size,
					)
					if not candidate_unit_ids:
						continue
					unit_id = _find_unit_for_window(
						date_key=date_key,
						window_start=start_slot,
						slots_needed=slots_needed,
						slot_size=slot_size,
						unit_slot_map=unit_slot_map,
						candidate_unit_ids=candidate_unit_ids,
					)
					if not unit_id:
						continue
					unit_name = unit_names.get(unit_id)

				reserve_start_dt = datetime.combine(date_key, start_slot)
				customer_start_dt = reserve_start_dt + timedelta(minutes=buffer_before)
				customer_end_dt = customer_start_dt + timedelta(minutes=duration)

				results.append(
					{
						"provider": provider,
						"provider_name": provider_names.get(provider),
						"service_unit": unit_id,
						"service_unit_name": unit_name,
						"date": date_key,
						"start_time": customer_start_dt.time(),
						"end_time": customer_end_dt.time(),
						"duration": duration,
						"buffer_before": buffer_before,
						"buffer_after": buffer_after,
						"slot_ids": [],
					}
				)

	results.sort(key=lambda row: (row["date"], row["start_time"], row.get("provider_name") or ""))
	return results


def _counter_table_ready() -> bool:
	try:
		return bool(frappe.db.table_exists("Resource Availability Counter"))
	except Exception:
		return False


def _get_slot_size_minutes() -> int:
	settings = frappe.get_cached_doc("Service Appointment Settings")
	return max(1, cint(settings.default_slot_size or 15))


def _build_shift_capacity_slots(
	target_date,
	slot_size_minutes: int,
	resource_type: str | None,
	resource_reference: str | None,
) -> dict[tuple[str, str, str], dict[str, Any]]:
	assignments = frappe.get_all(
		"Service Provider Shift Assignment",
		filters={
			"docstatus": 1,
			"status": "Active",
			"start_date": ["<=", target_date],
		},
		fields=[
			"name",
			"provider",
			"service_unit",
			"shift_type",
			"repeat_type",
			"monday",
			"tuesday",
			"wednesday",
			"thursday",
			"friday",
			"saturday",
			"sunday",
		],
	)

	if resource_type:
		assignments = [
			row
			for row in assignments
			if (
				(resource_type == "Service Provider" and row.provider == resource_reference)
				or (resource_type == "Service Unit" and row.service_unit == resource_reference)
			)
		]

	shift_types = {
		row["name"]: row
		for row in frappe.get_all(
			"Service Provider Shift Type",
			fields=["name", "start_time", "end_time", "break_start_time", "break_end_time"],
		)
	}

	provider_active = set(frappe.get_all("Service Provider", filters={"active": 1}, pluck="name"))
	unit_rows = {
		row["name"]: row
		for row in frappe.get_all(
			"Service Unit",
			fields=["name", "capacity", "allow_overlap", "allow_appointments", "disabled"],
		)
	}

	slots: dict[tuple[str, str, str], dict[str, Any]] = {}
	for assignment in assignments:
		if assignment.provider not in provider_active:
			continue
		if assignment.get("end_date") and getdate(assignment.end_date) < target_date:
			continue
		if not _assignment_matches_date(assignment, target_date):
			continue

		shift = shift_types.get(assignment.shift_type)
		if not shift:
			continue

		provider_max_capacity = 1.0
		for slot_time, is_break in _build_shift_slot_sequence(shift, target_date, slot_size_minutes):
			_provider_key = ("Service Provider", assignment.provider, slot_time)
			_merge_slot_entry(
				slots,
				_provider_key,
				max_capacity=provider_max_capacity,
				is_break=is_break,
				source_reference=assignment.name,
			)

		if assignment.service_unit:
			unit = unit_rows.get(assignment.service_unit)
			if not unit or unit.get("disabled") or not unit.get("allow_appointments"):
				continue

			unit_capacity = flt(unit.get("capacity") or 1.0)
			if not cint(unit.get("allow_overlap")):
				unit_capacity = 1.0

			for slot_time, is_break in _build_shift_slot_sequence(shift, target_date, slot_size_minutes):
				_unit_key = ("Service Unit", assignment.service_unit, slot_time)
				_merge_slot_entry(
					slots,
					_unit_key,
					max_capacity=unit_capacity,
					is_break=is_break,
					source_reference=assignment.name,
				)

	if resource_type and resource_type not in ("Service Provider", "Service Unit", "Equipment"):
		return {}

	if resource_type == "Equipment":
		return {}

	_apply_provider_unavailability_blocks(
		slots=slots,
		target_date=target_date,
		slot_size_minutes=slot_size_minutes,
		resource_type=resource_type,
		resource_reference=resource_reference,
	)

	return slots


def _apply_provider_unavailability_blocks(
	slots: dict[tuple[str, str, str], dict[str, Any]],
	target_date,
	slot_size_minutes: int,
	resource_type: str | None,
	resource_reference: str | None,
) -> None:
	if resource_type and resource_type != "Service Provider":
		return
	if not frappe.db.table_exists("Service Provider Unavailability"):
		return

	provider_ids = {
		key[1]
		for key in slots
		if key[0] == "Service Provider" and (not resource_reference or key[1] == resource_reference)
	}
	if not provider_ids:
		return

	rows = frappe.get_all(
		"Service Provider Unavailability",
		filters={
			"provider": ["in", list(provider_ids)],
			"status": "Active",
			"docstatus": 1,
			"from_date": ["<=", target_date],
			"to_date": [">=", target_date],
		},
		fields=[
			"name",
			"provider",
			"reason",
			"source",
			"all_day",
			"from_time",
			"to_time",
		],
	)
	if not rows:
		return

	by_provider: dict[str, list[dict[str, Any]]] = defaultdict(list)
	for row in rows:
		by_provider[row["provider"]].append(row)

	step = timedelta(minutes=slot_size_minutes)
	for key, slot in slots.items():
		r_type, provider, slot_time = key
		if r_type != "Service Provider":
			continue

		slot_unavailability = _find_unavailability_for_slot(
			unavailability_rows=by_provider.get(provider) or [],
			target_date=target_date,
			slot_time=slot_time,
			step=step,
		)
		if not slot_unavailability:
			continue

		slot["is_blocked"] = 1
		slot["block_reason"] = _format_unavailability_block_reason(slot_unavailability)
		slot["source_type"] = "Unavailability"
		slot["source_reference"] = slot_unavailability["name"]


def _find_unavailability_for_slot(
	unavailability_rows: list[dict[str, Any]],
	target_date,
	slot_time: str,
	step: timedelta,
) -> dict[str, Any] | None:
	slot_start = datetime.combine(target_date, get_time(slot_time))
	slot_end = slot_start + step

	for row in unavailability_rows:
		if cint(row.get("all_day") or 0):
			return row

		if not row.get("from_time") or not row.get("to_time"):
			continue

		unavailable_start = datetime.combine(target_date, get_time(row["from_time"]))
		unavailable_end = datetime.combine(target_date, get_time(row["to_time"]))
		if unavailable_end <= unavailable_start:
			unavailable_end = unavailable_end + timedelta(days=1)

		if slot_start < unavailable_end and slot_end > unavailable_start:
			return row

	return None


def _format_unavailability_block_reason(row: dict[str, Any]) -> str:
	reason = row.get("reason") or "Unavailable"
	source = row.get("source")
	if source and source != "Manual":
		return f"{reason} ({source})"
	return reason


def _merge_slot_entry(
	slots: dict[tuple[str, str, str], dict[str, Any]],
	key: tuple[str, str, str],
	max_capacity: float,
	is_break: bool,
	source_reference: str,
) -> None:
	row = slots.get(key)
	if not row:
		slots[key] = {
			"max_capacity": max_capacity,
			"is_blocked": 1 if is_break else 0,
			"block_reason": "Break" if is_break else None,
			"source_type": "Break" if is_break else "Shift",
			"source_reference": source_reference,
		}
		return

	row["max_capacity"] = max(flt(row.get("max_capacity") or 0), flt(max_capacity))
	if is_break:
		row["is_blocked"] = 1
		row["block_reason"] = "Break"
		row["source_type"] = "Break"


def _build_consumption_map(
	target_date,
	slot_size_minutes: int,
	resource_type: str | None,
	resource_reference: str | None,
) -> dict[tuple[str, str, str], float]:
	filters: dict[str, Any] = {
		"allocation_date": target_date,
		"allocation_status": ["in", ACTIVE_ALLOCATION_STATUSES],
	}
	if resource_type:
		filters["resource_type"] = resource_type
	if resource_reference:
		filters["resource_reference"] = resource_reference

	allocations = frappe.get_all(
		"Service Resource Allocation",
		filters=filters,
		fields=["resource_type", "resource_reference", "start_time", "end_time", "capacity_consumed"],
	)

	consumption: dict[tuple[str, str, str], float] = defaultdict(float)
	for allocation in allocations:
		slot_times = _interval_to_slot_times(
			target_date,
			allocation["start_time"],
			allocation["end_time"],
			slot_size_minutes,
		)
		for slot_time in slot_times:
			key = (
				allocation["resource_type"],
				allocation["resource_reference"],
				slot_time,
			)
			consumption[key] += flt(allocation.get("capacity_consumed") or 0.0)

	return consumption


def _delete_existing_counters(target_date, resource_type: str | None, resource_reference: str | None) -> None:
	filters: dict[str, Any] = {"counter_date": target_date}
	if resource_type:
		filters["resource_type"] = resource_type
	if resource_reference:
		filters["resource_reference"] = resource_reference

	frappe.db.delete("Resource Availability Counter", filters)


def _assignment_matches_date(assignment: frappe._dict, target_date) -> bool:
	if assignment.repeat_type == "Daily":
		return True

	if assignment.repeat_type != "Weekly":
		return True

	weekday_field = WEEKDAY_FIELD_MAP.get(target_date.weekday())
	if not weekday_field:
		return False
	return cint(assignment.get(weekday_field) or 0) == 1


def _build_shift_slot_sequence(
	shift: dict[str, Any],
	target_date,
	slot_size_minutes: int,
) -> list[tuple[str, bool]]:
	start_dt = datetime.combine(target_date, get_time(shift["start_time"]))
	end_dt = datetime.combine(target_date, get_time(shift["end_time"]))
	if end_dt <= start_dt:
		end_dt = end_dt + timedelta(days=1)

	break_start = shift.get("break_start_time")
	break_end = shift.get("break_end_time")
	break_start_dt = break_end_dt = None
	if break_start and break_end:
		break_start_dt = datetime.combine(target_date, get_time(break_start))
		break_end_dt = datetime.combine(target_date, get_time(break_end))
		# For overnight shifts, treat break times earlier than shift start as next-day breaks.
		if end_dt.date() > start_dt.date() and break_start_dt < start_dt:
			break_start_dt = break_start_dt + timedelta(days=1)
			break_end_dt = break_end_dt + timedelta(days=1)
		if break_end_dt <= break_start_dt:
			break_end_dt = break_end_dt + timedelta(days=1)

	rows: list[tuple[str, bool]] = []
	cursor = start_dt
	step = timedelta(minutes=slot_size_minutes)
	while cursor + step <= end_dt:
		if cursor.date() == target_date:
			slot_end = cursor + step
			is_break = False
			if break_start_dt and break_end_dt:
				is_break = slot_end > break_start_dt and cursor < break_end_dt
			rows.append((cursor.time().strftime("%H:%M:%S"), is_break))
		cursor += step

	return rows


def _interval_to_slot_times(target_date, start_time, end_time, slot_size_minutes: int) -> list[str]:
	interval_start = datetime.combine(target_date, get_time(start_time))
	interval_end = datetime.combine(target_date, get_time(end_time))
	if interval_end <= interval_start:
		interval_end = interval_end + timedelta(days=1)

	day_start = datetime.combine(target_date, time(0, 0, 0))
	day_end = day_start + timedelta(days=1)
	clamped_start = max(interval_start, day_start)
	clamped_end = min(interval_end, day_end)
	if clamped_end <= clamped_start:
		return []

	total_minutes_from_midnight = (clamped_start - day_start).total_seconds() / 60
	slot_index = int(total_minutes_from_midnight // slot_size_minutes)
	slot_cursor = day_start + timedelta(minutes=slot_index * slot_size_minutes)
	step = timedelta(minutes=slot_size_minutes)

	results: list[str] = []
	while slot_cursor < clamped_end:
		slot_end = slot_cursor + step
		if slot_end > clamped_start and slot_cursor < clamped_end:
			results.append(slot_cursor.time().strftime("%H:%M:%S"))
		slot_cursor += step

	return results


def _service_type_requires_unit(service_type_id: str) -> tuple[bool, list[str]]:
	rows = frappe.get_all(
		"Service Type Unit Type",
		filters={"parent": service_type_id},
		fields=["service_unit_type"],
	)
	unit_types = [row["service_unit_type"] for row in rows if row.get("service_unit_type")]
	return (len(unit_types) > 0, unit_types)


def _get_service_providers(service_type_id: str, provider_id: str | None) -> list[str]:
	if provider_id:
		is_valid = frappe.db.exists(
			"Service Provider Service",
			{"parent": provider_id, "service_type": service_type_id, "disabled": 0},
		)
		if not is_valid:
			return []
		is_active = frappe.db.exists("Service Provider", {"name": provider_id, "active": 1})
		return [provider_id] if is_active else []

	provider_rows = frappe.db.sql(
		"""
		SELECT DISTINCT sps.parent
		FROM `tabService Provider Service` sps
		INNER JOIN `tabService Provider` sp ON sps.parent = sp.name
		WHERE sps.service_type = %(service_type)s
		  AND sps.disabled = 0
		  AND sp.active = 1
	""",
		{"service_type": service_type_id},
		as_dict=True,
	)
	return [row["parent"] for row in provider_rows]


def _build_available_slot_map(counter_rows: list[dict[str, Any]]) -> dict[str, dict[Any, list[time]]]:
	resource_date_slots: dict[str, dict[Any, list[time]]] = defaultdict(lambda: defaultdict(list))
	for row in counter_rows:
		if flt(row.get("remaining_capacity") or 0) <= 0:
			continue
		if cint(row.get("is_blocked") or 0) == 1:
			continue
		resource = row["resource_reference"]
		date_key = row["counter_date"]
		slot_time = get_time(row["counter_slot_time"])
		resource_date_slots[resource][date_key].append(slot_time)

	for resource in resource_date_slots:
		for date_key in resource_date_slots[resource]:
			resource_date_slots[resource][date_key] = sorted(set(resource_date_slots[resource][date_key]))

	return resource_date_slots


def _find_contiguous_windows(
	slot_times: list[time],
	slot_size_minutes: int,
	slots_needed: int,
) -> list[time]:
	if not slot_times or slots_needed <= 0:
		return []

	step = timedelta(minutes=slot_size_minutes)
	slots = sorted(slot_times)
	results: list[time] = []

	for i in range(len(slots)):
		window_ok = True
		for offset in range(slots_needed - 1):
			left = datetime.combine(datetime.today(), slots[i + offset])
			right = (
				datetime.combine(datetime.today(), slots[i + offset + 1])
				if i + offset + 1 < len(slots)
				else None
			)
			if not right or (right - left) != step:
				window_ok = False
				break
		if window_ok and i + slots_needed <= len(slots):
			results.append(slots[i])

	return results


def _find_unit_for_window(
	date_key,
	window_start: time,
	slots_needed: int,
	slot_size: int,
	unit_slot_map: dict[str, dict[Any, list[time]]],
	candidate_unit_ids: set[str] | None = None,
) -> str | None:
	step = timedelta(minutes=slot_size)
	required = []
	cursor = datetime.combine(datetime.today(), window_start)
	for _ in range(slots_needed):
		required.append(cursor.time())
		cursor += step

	required_set = set(required)
	for unit_id, date_map in unit_slot_map.items():
		if candidate_unit_ids is not None and unit_id not in candidate_unit_ids:
			continue
		available = set(date_map.get(date_key, []))
		if required_set.issubset(available):
			return unit_id

	return None


def _build_provider_unit_shift_map(
	start,
	end,
	provider_ids: list[str],
	allowed_unit_ids: set[str],
	slot_size_minutes: int,
) -> dict[str, dict[Any, dict[str, set[time]]]]:
	if not provider_ids or not allowed_unit_ids:
		return {}

	assignments = frappe.get_all(
		"Service Provider Shift Assignment",
		filters={
			"docstatus": 1,
			"status": "Active",
			"provider": ["in", provider_ids],
			"service_unit": ["is", "set"],
			"start_date": ["<=", end],
		},
		fields=[
			"provider",
			"service_unit",
			"shift_type",
			"repeat_type",
			"start_date",
			"end_date",
			"monday",
			"tuesday",
			"wednesday",
			"thursday",
			"friday",
			"saturday",
			"sunday",
		],
	)

	shift_types = {
		row["name"]: row
		for row in frappe.get_all(
			"Service Provider Shift Type",
			fields=["name", "start_time", "end_time", "break_start_time", "break_end_time"],
		)
	}

	provider_unit_slots: dict[str, dict[Any, dict[str, set[time]]]] = defaultdict(
		lambda: defaultdict(lambda: defaultdict(set))
	)

	for assignment in assignments:
		service_unit = assignment.get("service_unit")
		if not service_unit or service_unit not in allowed_unit_ids:
			continue

		shift = shift_types.get(assignment.get("shift_type"))
		if not shift:
			continue

		assignment_start = max(start, getdate(assignment.get("start_date")))
		assignment_end = end
		if assignment.get("end_date"):
			assignment_end = min(end, getdate(assignment.get("end_date")))
		if assignment_end < start or assignment_end < assignment_start:
			continue

		current = assignment_start
		while current <= assignment_end:
			if _assignment_matches_date(assignment, current):
				for slot_time, is_break in _build_shift_slot_sequence(shift, current, slot_size_minutes):
					if is_break:
						continue
					provider_unit_slots[assignment.provider][current][service_unit].add(get_time(slot_time))
			current = add_days(current, 1)

	return provider_unit_slots


def _get_provider_window_candidate_units(
	provider_unit_shift_map: dict[str, dict[Any, dict[str, set[time]]]],
	provider: str,
	date_key,
	window_start: time,
	slots_needed: int,
	slot_size_minutes: int,
) -> set[str]:
	date_units = provider_unit_shift_map.get(provider, {}).get(date_key, {})
	if not date_units:
		return set()

	step = timedelta(minutes=slot_size_minutes)
	required_slots: set[time] = set()
	cursor = datetime.combine(datetime.today(), window_start)
	for _ in range(slots_needed):
		required_slots.add(cursor.time())
		cursor += step

	eligible: set[str] = set()
	for unit_id, unit_slots in date_units.items():
		if required_slots.issubset(unit_slots):
			eligible.add(unit_id)

	return eligible


def enqueue_targeted_counter_refresh(
	start_date,
	end_date,
	provider: str | None = None,
	service_unit: str | None = None,
) -> None:
	"""Queue immediate targeted projection refresh for provider/service unit resources."""
	if not provider and not service_unit:
		return

	try:
		start = getdate(start_date)
		end = getdate(end_date)
	except Exception:
		return

	if end < start:
		start, end = end, start

	frappe.enqueue(
		"frappoint.frappoint.services.availability_projector.refresh_targeted_counters",
		queue="short",
		timeout=1500,
		enqueue_after_commit=True,
		start_date=str(start),
		end_date=str(end),
		provider=provider,
		service_unit=service_unit,
	)


def refresh_targeted_counters(
	start_date,
	end_date,
	provider: str | None = None,
	service_unit: str | None = None,
) -> dict[str, Any]:
	"""Refresh projection counters immediately for specific resources and date window."""
	if not provider and not service_unit:
		return {"start_date": str(start_date), "end_date": str(end_date), "days": 0, "results": []}

	start = getdate(start_date)
	end = getdate(end_date)
	if end < start:
		start, end = end, start

	results: list[dict[str, Any]] = []
	current = start
	while current <= end:
		if provider:
			results.append(
				rebuild_counter_for_date(
					counter_date=current,
					resource_type="Service Provider",
					resource_reference=provider,
				)
			)
		if service_unit:
			results.append(
				rebuild_counter_for_date(
					counter_date=current,
					resource_type="Service Unit",
					resource_reference=service_unit,
				)
			)
		frappe.db.commit()
		current = add_days(current, 1)

	return {
		"start_date": str(start),
		"end_date": str(end),
		"provider": provider,
		"service_unit": service_unit,
		"days": (end - start).days + 1,
		"results": results,
	}


def refresh_counter_horizon() -> dict[str, Any]:
	"""Scheduled job entrypoint to keep counters hot for booking horizon."""
	settings = frappe.get_cached_doc("Service Appointment Settings")
	horizon = cint(settings.max_advance_days or 30)
	start = add_days(getdate(nowdate()), -1)
	end = add_days(getdate(nowdate()), horizon)

	# Rebuild one day at a time to avoid transaction write limits on large horizons.
	results = []
	current = start
	while current <= end:
		results.append(rebuild_counter_for_date(current))
		frappe.db.commit()
		current = add_days(current, 1)

	result = {
		"start_date": str(start),
		"end_date": str(end),
		"days": len(results),
		"results": results,
	}
	frappe.logger().info(
		"Availability counter horizon refresh complete: %s -> %s (%s days)",
		result["start_date"],
		result["end_date"],
		result["days"],
	)
	return result
