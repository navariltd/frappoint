from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import get_time, getdate

from frappoint.frappoint.doctype.service_provider_appointment_slot.service_provider_appointment_slot import (
	_get_provider_change_options,
	change_appointment_provider,
)

ACTIVE_APPOINTMENT_STATUSES = ("Open", "Pending Payment", "Confirmed", "Checked In", "In Progress")


def get_affected_appointments(
	provider: str,
	from_date,
	to_date,
	from_time=None,
	to_time=None,
	all_day: bool = True,
) -> list[dict[str, Any]]:
	"""Return active appointments affected by a provider unavailability window."""
	if not provider or not from_date or not to_date:
		return []

	start = getdate(from_date)
	end = getdate(to_date)
	if end < start:
		start, end = end, start

	filters: dict[str, Any] = {
		"appointment_provider": provider,
		"appointment_date": ["between", [start, end]],
		"status": ["in", ACTIVE_APPOINTMENT_STATUSES],
		"docstatus": ["!=", 2],
	}

	rows = frappe.get_all(
		"Service Appointment",
		filters=filters,
		fields=[
			"name",
			"booking_id",
			"appointment_type",
			"appointment_date",
			"start_time",
			"end_time",
			"appointment_provider",
			"service_provider_name",
			"service_unit",
			"status",
			"full_name",
			"customer",
		],
		order_by="appointment_date asc, start_time asc",
	)

	if all_day or not from_time or not to_time:
		return rows

	unavailable_start = get_time(from_time)
	unavailable_end = get_time(to_time)
	return [
		row
		for row in rows
		if row.get("start_time")
		and row.get("end_time")
		and get_time(row["start_time"]) < unavailable_end
		and get_time(row["end_time"]) > unavailable_start
	]


def get_affected_appointments_for_unavailability(unavailability_name: str) -> list[dict[str, Any]]:
	if not unavailability_name:
		return []

	doc = frappe.get_doc("Service Provider Unavailability", unavailability_name)
	return get_affected_appointments(
		provider=doc.provider,
		from_date=doc.from_date,
		to_date=doc.to_date,
		from_time=doc.from_time,
		to_time=doc.to_time,
		all_day=bool(doc.all_day),
	)


@frappe.whitelist()
def get_reassignment_preview(
	unavailability_name: str | None = None,
	provider: str | None = None,
	from_date=None,
	to_date=None,
	from_time=None,
	to_time=None,
	all_day: bool = True,
) -> dict[str, Any]:
	"""Return affected appointments and available replacement providers."""
	_assert_can_manage_unavailability()

	if unavailability_name:
		unavailability = frappe.get_doc("Service Provider Unavailability", unavailability_name)
		appointments = get_affected_appointments_for_unavailability(unavailability_name)
		context = _serialize_unavailability_context(unavailability)
	else:
		appointments = get_affected_appointments(
			provider=provider,
			from_date=from_date,
			to_date=to_date,
			from_time=from_time,
			to_time=to_time,
			all_day=bool(all_day),
		)
		context = {
			"provider": provider,
			"from_date": from_date,
			"to_date": to_date,
			"from_time": from_time,
			"to_time": to_time,
			"all_day": bool(all_day),
		}

	return {
		"success": True,
		"context": context,
		"affected_count": len(appointments),
		"appointments": [_build_reassignment_candidate(row) for row in appointments],
	}


@frappe.whitelist()
def reassign_affected_appointments(
	unavailability_name: str,
	assignments=None,
	auto_assign: bool = True,
) -> dict[str, Any]:
	"""Reassign appointments affected by one unavailability record.

	`assignments` may be a JSON string/list of rows with appointment, provider,
	and optional service_unit. When `auto_assign` is true, rows without explicit
	assignments use the first fair replacement option from the preview.
	"""
	_assert_can_manage_unavailability()

	if not unavailability_name:
		frappe.throw(_("Unavailability is required."))

	unavailability = frappe.get_doc("Service Provider Unavailability", unavailability_name)
	assignment_map = _normalize_assignment_map(assignments)
	affected = get_affected_appointments_for_unavailability(unavailability.name)
	results = []

	for row in affected:
		appointment_name = row.get("name")
		candidate = _build_reassignment_candidate(row)
		requested = assignment_map.get(appointment_name) or {}
		target_provider = requested.get("provider")
		target_service_unit = requested.get("service_unit")

		if not target_provider and bool(auto_assign):
			recommended = candidate.get("recommended_option") or {}
			target_provider = recommended.get("provider")
			target_service_unit = recommended.get("service_unit")

		if not target_provider:
			results.append(
				{
					"appointment": appointment_name,
					"success": False,
					"skipped": True,
					"message": _("No replacement provider selected or available."),
					"options": candidate.get("provider_change_options") or [],
				}
			)
			continue

		try:
			result = change_appointment_provider(
				appointment_name,
				target_provider=target_provider,
				target_service_unit=target_service_unit,
			)
			results.append(
				{
					"appointment": appointment_name,
					"success": True,
					"provider": result.get("current_provider"),
					"provider_name": result.get("provider_name"),
					"message": result.get("message"),
				}
			)
		except Exception as exc:
			frappe.db.rollback()
			results.append(
				{
					"appointment": appointment_name,
					"success": False,
					"message": str(exc),
					"options": candidate.get("provider_change_options") or [],
				}
			)

	success_count = len([row for row in results if row.get("success")])
	skipped_count = len([row for row in results if row.get("skipped")])

	return {
		"success": True,
		"unavailability": unavailability.name,
		"affected_count": len(affected),
		"reassigned_count": success_count,
		"skipped_count": skipped_count,
		"failed_count": len(affected) - success_count - skipped_count,
		"results": results,
	}


def _build_reassignment_candidate(row) -> dict[str, Any]:
	appointment = frappe.get_doc("Service Appointment", row.get("name"))
	options = _get_provider_change_options(appointment)
	recommended = options[0] if options else None

	return {
		"name": appointment.name,
		"booking_id": appointment.booking_id,
		"appointment_type": appointment.appointment_type,
		"appointment_date": appointment.appointment_date,
		"start_time": appointment.start_time,
		"end_time": appointment.end_time,
		"status": appointment.status,
		"customer": appointment.customer,
		"full_name": appointment.full_name,
		"current_provider": appointment.appointment_provider,
		"current_provider_name": appointment.service_provider_name
		or frappe.db.get_value("Service Provider", appointment.appointment_provider, "provider_name")
		or appointment.appointment_provider,
		"service_unit": appointment.service_unit,
		"provider_change_options": options,
		"recommended_option": recommended,
	}


def _normalize_assignment_map(assignments) -> dict[str, dict[str, Any]]:
	if not assignments:
		return {}
	if isinstance(assignments, str):
		assignments = frappe.parse_json(assignments)

	normalized = {}
	for row in assignments or []:
		row = frappe._dict(row or {})
		appointment = row.get("appointment") or row.get("appointment_name") or row.get("name")
		provider = row.get("provider") or row.get("target_provider")
		if not appointment or not provider:
			continue
		normalized[appointment] = {
			"provider": provider,
			"service_unit": row.get("service_unit") or row.get("target_service_unit"),
		}
	return normalized


def _serialize_unavailability_context(unavailability) -> dict[str, Any]:
	return {
		"name": unavailability.name,
		"provider": unavailability.provider,
		"provider_name": unavailability.provider_name,
		"from_date": unavailability.from_date,
		"to_date": unavailability.to_date,
		"from_time": unavailability.from_time,
		"to_time": unavailability.to_time,
		"all_day": bool(unavailability.all_day),
		"reason": unavailability.reason,
		"source": unavailability.source,
		"source_doctype": unavailability.source_doctype,
		"source_name": unavailability.source_name,
	}


def _assert_can_manage_unavailability() -> None:
	roles = set(frappe.get_roles())
	allowed_roles = {"System Manager", "HR Manager", "Service Manager"}
	if roles.isdisjoint(allowed_roles):
		frappe.throw(
			_("You do not have permission to manage provider unavailability."), frappe.PermissionError
		)
