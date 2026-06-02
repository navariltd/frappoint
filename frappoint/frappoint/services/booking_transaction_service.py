from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, get_time, getdate, now_datetime

from frappoint.frappoint.services.availability_projector import rebuild_counter_for_date

ACTIVE_RESERVATION_STATUSES = ("Draft", "Held", "Confirmed")


class CapacityReservationError(frappe.ValidationError):
	pass


def reserve_and_create_allocations(
	appointment_name: str,
	allocations: list[dict[str, Any]],
	booking_name: str | None = None,
	allocation_status: str = "Held",
	extra_metadata: dict[str, Any] | None = None,
	commit: bool = False,
) -> list[str]:
	"""Atomically reserve counter capacity and create allocation ledger rows.

	Each allocation payload expects:
	- resource_type
	- resource_reference
	- allocation_date
	- start_time
	- end_time
	- appointment_start_time
	- appointment_end_time
	Optional:
	- capacity_consumed (default 1)
	- buffer_before_minutes (default 0)
	- buffer_after_minutes (default 0)
	"""
	if not allocations:
		return []

	if not frappe.db.exists("Service Appointment", appointment_name):
		raise CapacityReservationError(_("Service Appointment {0} not found").format(appointment_name))

	savepoint = _savepoint_name("reserve")
	frappe.db.savepoint(savepoint)
	created_names: list[str] = []

	try:
		prepared = [_prepare_allocation_payload(row) for row in allocations]
		_ensure_counter_rows(prepared)
		_apply_counter_deltas(prepared, direction="reserve")

		for row in prepared:
			doc = frappe.get_doc(
				{
					"doctype": "Service Resource Allocation",
					"allocation_date": row["allocation_date"],
					"service_appointment": appointment_name,
					"service_booking": booking_name,
					"resource_type": row["resource_type"],
					"resource_reference": row["resource_reference"],
					"start_time": row["start_time"],
					"end_time": row["end_time"],
					"appointment_start_time": row["appointment_start_time"],
					"appointment_end_time": row["appointment_end_time"],
					"capacity_consumed": row["capacity_consumed"],
					"buffer_before_minutes": row["buffer_before_minutes"],
					"buffer_after_minutes": row["buffer_after_minutes"],
					"allocation_status": allocation_status,
					"metadata_json": {
						"source": "booking_transaction_service",
						**(extra_metadata or {}),
					},
				}
			)
			doc.insert(ignore_permissions=True)
			created_names.append(doc.name)

		_update_appointment_allocation_status(appointment_name, allocation_status)
		if commit:
			frappe.db.commit()
		return created_names
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def release_capacity_for_allocations(
	allocation_names: list[str] | None = None,
	appointment_name: str | None = None,
	target_status: str = "Released",
	commit: bool = False,
) -> int:
	"""Atomically release reserved/confirmed capacity for existing allocations."""
	if not allocation_names and not appointment_name:
		return 0

	filters: dict[str, Any] = {"allocation_status": ["in", list(ACTIVE_RESERVATION_STATUSES)]}
	if allocation_names:
		filters["name"] = ["in", allocation_names]
	if appointment_name:
		filters["service_appointment"] = appointment_name

	rows = frappe.get_all(
		"Service Resource Allocation",
		filters=filters,
		fields=[
			"name",
			"allocation_date",
			"resource_type",
			"resource_reference",
			"start_time",
			"end_time",
			"capacity_consumed",
		],
	)
	if not rows:
		return 0

	savepoint = _savepoint_name("release")
	frappe.db.savepoint(savepoint)

	try:
		prepared = [_prepare_release_payload(row) for row in rows]
		_apply_counter_deltas(prepared, direction="release")

		for row in rows:
			frappe.db.set_value(
				"Service Resource Allocation",
				row["name"],
				{
					"allocation_status": target_status,
					"is_confirmed": 0,
					"confirmed_at": None,
				},
				update_modified=False,
			)

		if appointment_name:
			_update_appointment_allocation_status(appointment_name, target_status)

		if commit:
			frappe.db.commit()
		return len(rows)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def confirm_held_allocations(appointment_name: str, commit: bool = False) -> int:
	"""Move held allocations to confirmed and sync appointment status field."""
	rows = frappe.get_all(
		"Service Resource Allocation",
		filters={"service_appointment": appointment_name, "allocation_status": "Held"},
		pluck="name",
	)
	if not rows:
		return 0

	now = now_datetime()
	for name in rows:
		frappe.db.set_value(
			"Service Resource Allocation",
			name,
			{"allocation_status": "Confirmed", "is_confirmed": 1, "confirmed_at": now},
			update_modified=False,
		)

	_update_appointment_allocation_status(appointment_name, "Confirmed")
	if commit:
		frappe.db.commit()
	return len(rows)


def _prepare_allocation_payload(payload: dict[str, Any]) -> dict[str, Any]:
	required = [
		"resource_type",
		"resource_reference",
		"allocation_date",
		"start_time",
		"end_time",
		"appointment_start_time",
		"appointment_end_time",
	]
	missing = [k for k in required if not payload.get(k)]
	if missing:
		raise CapacityReservationError(_("Missing allocation fields: {0}").format(", ".join(missing)))

	prepared = {
		"resource_type": payload["resource_type"],
		"resource_reference": payload["resource_reference"],
		"allocation_date": getdate(payload["allocation_date"]),
		"start_time": _time_str(payload["start_time"]),
		"end_time": _time_str(payload["end_time"]),
		"appointment_start_time": _time_str(payload["appointment_start_time"]),
		"appointment_end_time": _time_str(payload["appointment_end_time"]),
		"capacity_consumed": flt(payload.get("capacity_consumed") or 1.0),
		"buffer_before_minutes": cint(payload.get("buffer_before_minutes") or 0),
		"buffer_after_minutes": cint(payload.get("buffer_after_minutes") or 0),
	}
	if prepared["capacity_consumed"] <= 0:
		raise CapacityReservationError(_("capacity_consumed must be greater than zero"))

	return prepared


def _prepare_release_payload(payload: dict[str, Any]) -> dict[str, Any]:
	return {
		"resource_type": payload["resource_type"],
		"resource_reference": payload["resource_reference"],
		"allocation_date": getdate(payload["allocation_date"]),
		"start_time": _time_str(payload["start_time"]),
		"end_time": _time_str(payload["end_time"]),
		"capacity_consumed": flt(payload.get("capacity_consumed") or 1.0),
	}


def _ensure_counter_rows(prepared: list[dict[str, Any]]) -> None:
	"""Ensure relevant counter rows exist by rebuilding missing resource/date projections."""
	pairs = {(p["allocation_date"], p["resource_type"], p["resource_reference"]) for p in prepared}
	for allocation_date, resource_type, resource_reference in pairs:
		counter_exists = frappe.db.exists(
			"Resource Availability Counter",
			{
				"counter_date": allocation_date,
				"resource_type": resource_type,
				"resource_reference": resource_reference,
			},
		)
		if not counter_exists:
			rebuild_counter_for_date(
				counter_date=allocation_date,
				resource_type=resource_type,
				resource_reference=resource_reference,
			)


def _apply_counter_deltas(prepared: list[dict[str, Any]], direction: str) -> None:
	slot_size = _slot_size_minutes()
	if direction not in ("reserve", "release"):
		raise CapacityReservationError(_("Unsupported counter delta direction: {0}").format(direction))

	for row in prepared:
		slots = _slot_times_for_interval(
			row["allocation_date"], row["start_time"], row["end_time"], slot_size
		)
		for slot_time in slots:
			frappe.db.sql(
				"""
				SELECT name
				FROM `tabResource Availability Counter`
				WHERE counter_date = %(counter_date)s
				  AND counter_slot_time = %(counter_slot_time)s
				  AND resource_type = %(resource_type)s
				  AND resource_reference = %(resource_reference)s
				FOR UPDATE
				""",
				{
					"counter_date": row["allocation_date"],
					"counter_slot_time": slot_time,
					"resource_type": row["resource_type"],
					"resource_reference": row["resource_reference"],
				},
			)

			if direction == "reserve":
				frappe.db.sql(
					"""
					UPDATE `tabResource Availability Counter`
					SET
						consumed_capacity = consumed_capacity + %(qty)s,
						remaining_capacity = remaining_capacity - %(qty)s
					WHERE counter_date = %(counter_date)s
					  AND counter_slot_time = %(counter_slot_time)s
					  AND resource_type = %(resource_type)s
					  AND resource_reference = %(resource_reference)s
					  AND is_blocked = 0
					  AND remaining_capacity >= %(qty)s
					""",
					{
						"qty": row["capacity_consumed"],
						"counter_date": row["allocation_date"],
						"counter_slot_time": slot_time,
						"resource_type": row["resource_type"],
						"resource_reference": row["resource_reference"],
					},
				)
				if _last_sql_rowcount() == 0:
					raise CapacityReservationError(
						_("Insufficient capacity for {0} {1} on {2} at {3}").format(
							row["resource_type"],
							row["resource_reference"],
							row["allocation_date"],
							slot_time,
						)
					)
			else:
				frappe.db.sql(
					"""
					UPDATE `tabResource Availability Counter`
					SET
						consumed_capacity = GREATEST(consumed_capacity - %(qty)s, 0),
						remaining_capacity = LEAST(remaining_capacity + %(qty)s, max_capacity)
					WHERE counter_date = %(counter_date)s
					  AND counter_slot_time = %(counter_slot_time)s
					  AND resource_type = %(resource_type)s
					  AND resource_reference = %(resource_reference)s
					""",
					{
						"qty": row["capacity_consumed"],
						"counter_date": row["allocation_date"],
						"counter_slot_time": slot_time,
						"resource_type": row["resource_type"],
						"resource_reference": row["resource_reference"],
					},
				)


def _last_sql_rowcount() -> int:
	cursor = getattr(frappe.db, "_cursor", None)
	if cursor is None:
		return 0
	return int(getattr(cursor, "rowcount", 0) or 0)


def _slot_times_for_interval(
	allocation_date, start_time_str: str, end_time_str: str, slot_size: int
) -> list[str]:
	start_dt = datetime.combine(allocation_date, get_time(start_time_str))
	end_dt = datetime.combine(allocation_date, get_time(end_time_str))
	if end_dt <= start_dt:
		end_dt = end_dt + timedelta(days=1)

	day_start = datetime.combine(allocation_date, time(0, 0, 0))
	day_end = day_start + timedelta(days=1)
	clamped_start = max(day_start, start_dt)
	clamped_end = min(day_end, end_dt)
	if clamped_end <= clamped_start:
		return []

	step = timedelta(minutes=slot_size)
	from_midnight = int((clamped_start - day_start).total_seconds() // 60)
	slot_index = from_midnight // slot_size
	cursor = day_start + timedelta(minutes=slot_index * slot_size)

	result: list[str] = []
	while cursor < clamped_end:
		slot_end = cursor + step
		if slot_end > clamped_start and cursor < clamped_end:
			result.append(cursor.time().strftime("%H:%M:%S"))
		cursor += step
	return result


def _update_appointment_allocation_status(appointment_name: str, status: str) -> None:
	if frappe.db.exists("DocField", {"parent": "Service Appointment", "fieldname": "allocation_status"}):
		frappe.db.set_value(
			"Service Appointment",
			appointment_name,
			"allocation_status",
			status if status in ("Held", "Confirmed", "Released") else "Released",
			update_modified=False,
		)


def _time_str(value) -> str:
	return get_time(value).strftime("%H:%M:%S")


def _slot_size_minutes() -> int:
	return max(1, cint(frappe.db.get_single_value("Service Appointment Settings", "default_slot_size") or 15))


def _savepoint_name(prefix: str) -> str:
	stamp = now_datetime().strftime("%H%M%S%f")
	return f"{prefix}_{stamp}"
