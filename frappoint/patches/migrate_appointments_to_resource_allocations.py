# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import frappe
from frappe.utils import cint, get_time

ACTIVE_APPOINTMENT_STATUSES = {
	"Open",
	"Pending Payment",
	"Confirmed",
	"Checked In",
	"In Progress",
	"Rescheduled",
	"Completed",
}

HELD_APPOINTMENT_STATUSES = {
	"Open",
	"Pending Payment",
}


def execute():
	"""Backfill Service Resource Allocation from existing Service Appointment records."""
	if not frappe.db.exists("DocType", "Service Resource Allocation"):
		frappe.logger().warning("Skipping allocation migration: Service Resource Allocation doctype missing")
		return

	last_name = ""
	batch_size = 500
	total_created = 0
	total_processed = 0

	while True:
		appointments = _fetch_appointments_batch(last_name=last_name, limit=batch_size)
		if not appointments:
			break

		for appointment in appointments:
			total_processed += 1
			created = _migrate_single_appointment(appointment)
			total_created += created
			last_name = appointment["name"]

		frappe.db.commit()

	frappe.logger().info(
		"Service allocation migration completed. processed=%s created=%s",
		total_processed,
		total_created,
	)


def _fetch_appointments_batch(last_name: str, limit: int) -> list[dict[str, Any]]:
	conditions = ["status IN %(statuses)s"]
	params: dict[str, Any] = {"statuses": tuple(ACTIVE_APPOINTMENT_STATUSES), "limit": limit}

	if last_name:
		conditions.append("name > %(last_name)s")
		params["last_name"] = last_name

	where_clause = " AND ".join(conditions)
	query = f"""
		SELECT
			name,
			booking_id,
			appointment_type,
			appointment_provider,
			service_unit,
			appointment_date,
			start_time,
			end_time,
			status
		FROM `tabService Appointment`
		WHERE {where_clause}
		ORDER BY name ASC
		LIMIT %(limit)s
	"""

	return frappe.db.sql(query, params, as_dict=True)


def _migrate_single_appointment(appointment: dict[str, Any]) -> int:
	"""Create missing allocation records for provider and service unit resources."""
	appointment_name = appointment["name"]
	appointment_date = appointment.get("appointment_date")
	start_time = appointment.get("start_time")
	end_time = appointment.get("end_time")

	if not appointment_date or not start_time or not end_time:
		frappe.logger().warning("Skipping appointment %s due to missing date/time fields", appointment_name)
		return 0

	buffer_before, buffer_after = _resolve_buffers(appointment.get("appointment_type"))
	allocation_start, allocation_end = _compute_allocation_window(
		appointment_date,
		start_time,
		end_time,
		buffer_before,
		buffer_after,
	)

	allocation_status = _map_appointment_status_to_allocation_status(appointment.get("status"))
	created_count = 0

	provider = appointment.get("appointment_provider")
	if provider:
		created_count += _create_allocation_if_missing(
			appointment=appointment,
			resource_type="Service Provider",
			resource_reference=provider,
			allocation_start=allocation_start,
			allocation_end=allocation_end,
			buffer_before=buffer_before,
			buffer_after=buffer_after,
			allocation_status=allocation_status,
		)

	service_unit = appointment.get("service_unit")
	if service_unit:
		created_count += _create_allocation_if_missing(
			appointment=appointment,
			resource_type="Service Unit",
			resource_reference=service_unit,
			allocation_start=allocation_start,
			allocation_end=allocation_end,
			buffer_before=buffer_before,
			buffer_after=buffer_after,
			allocation_status=allocation_status,
		)

	return created_count


def _resolve_buffers(appointment_type: str | None) -> tuple[int, int]:
	if not appointment_type:
		return 0, 0

	service_type = frappe.db.get_value(
		"Service Type",
		appointment_type,
		["buffer_before", "buffer_after"],
		as_dict=True,
	)
	if not service_type:
		return 0, 0

	return cint(service_type.get("buffer_before") or 0), cint(service_type.get("buffer_after") or 0)


def _compute_allocation_window(
	appointment_date,
	start_time,
	end_time,
	buffer_before: int,
	buffer_after: int,
) -> tuple[str, str]:
	start_dt = datetime.combine(appointment_date, get_time(start_time))
	end_dt = datetime.combine(appointment_date, get_time(end_time))

	allocation_start_dt = start_dt - timedelta(minutes=buffer_before)
	allocation_end_dt = end_dt + timedelta(minutes=buffer_after)

	return (
		allocation_start_dt.time().strftime("%H:%M:%S"),
		allocation_end_dt.time().strftime("%H:%M:%S"),
	)


def _map_appointment_status_to_allocation_status(status: str | None) -> str:
	if status in HELD_APPOINTMENT_STATUSES:
		return "Held"
	return "Confirmed"


def _create_allocation_if_missing(
	appointment: dict[str, Any],
	resource_type: str,
	resource_reference: str,
	allocation_start: str,
	allocation_end: str,
	buffer_before: int,
	buffer_after: int,
	allocation_status: str,
) -> int:
	filters = {
		"service_appointment": appointment["name"],
		"resource_type": resource_type,
		"resource_reference": resource_reference,
	}
	if frappe.db.exists("Service Resource Allocation", filters):
		return 0

	doc = frappe.get_doc(
		{
			"doctype": "Service Resource Allocation",
			"allocation_date": appointment["appointment_date"],
			"service_appointment": appointment["name"],
			"service_booking": appointment.get("booking_id"),
			"resource_type": resource_type,
			"resource_reference": resource_reference,
			"start_time": allocation_start,
			"end_time": allocation_end,
			"appointment_start_time": appointment["start_time"],
			"appointment_end_time": appointment["end_time"],
			"capacity_consumed": 1.0,
			"buffer_before_minutes": buffer_before,
			"buffer_after_minutes": buffer_after,
			"allocation_status": allocation_status,
			"metadata_json": {
				"migration_source": "phase_2_backfill",
				"appointment_status_at_migration": appointment.get("status"),
			},
		}
	)
	doc.insert(ignore_permissions=True)
	return 1
