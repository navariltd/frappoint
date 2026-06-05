from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, get_time, getdate, now_datetime

from frappoint.frappoint.services.appointment_state_service import log_appointment_event
from frappoint.frappoint.services.availability_projector import rebuild_counter_for_date
from frappoint.frappoint.services.booking_transaction_service import (
	release_capacity_for_allocations,
	reserve_and_create_allocations,
)
from frappoint.frappoint.services.provider_assignment_service import rank_provider_options

ACTIVE_ALLOCATION_STATUSES = ("Draft", "Held", "Confirmed")
ONGOING_STATUSES = ("Checked In", "In Progress")


@frappe.whitelist()
def get_ongoing_reassignment_options(
	appointment_name: str | None = None,
	handover_time: str | None = None,
	appointment_id: str | None = None,
	**kwargs,
) -> dict[str, Any]:
	appointment_name = (
		appointment_name or appointment_id or kwargs.get("appointmentId") or kwargs.get("appointment")
	)
	handover_time = handover_time or kwargs.get("handoverTime") or kwargs.get("actual_start_time")
	_assert_can_write_appointment(appointment_name)
	appointment = frappe.get_doc("Service Appointment", appointment_name)
	handover = _resolve_handover_time(appointment, handover_time)
	options = _get_replacement_options(appointment, handover)

	return {
		"success": True,
		"appointment": appointment.name,
		"current_provider": appointment.appointment_provider,
		"handover_time": handover.strftime("%H:%M:%S"),
		"provider_change_options": options,
	}


@frappe.whitelist()
def reassign_ongoing_appointment(
	appointment_name: str | None = None,
	target_provider: str | None = None,
	handover_time: str | None = None,
	reason: str | None = None,
	appointment_id: str | None = None,
	new_provider: str | None = None,
	provider: str | None = None,
	**kwargs,
) -> dict[str, Any]:
	appointment_name = (
		appointment_name or appointment_id or kwargs.get("appointmentId") or kwargs.get("appointment")
	)
	target_provider = (
		target_provider
		or new_provider
		or provider
		or kwargs.get("targetProvider")
		or kwargs.get("newProvider")
	)
	handover_time = handover_time or kwargs.get("handoverTime") or kwargs.get("actual_start_time")
	_assert_can_write_appointment(appointment_name)
	if not target_provider:
		frappe.throw(_("Replacement provider is required."))

	appointment = frappe.get_doc("Service Appointment", appointment_name)
	_assert_ongoing_appointment(appointment)
	if target_provider == appointment.appointment_provider:
		frappe.throw(_("Select a different provider for handover."))

	handover = _resolve_handover_time(appointment, handover_time)
	options = _get_replacement_options(appointment, handover)
	selected = next((row for row in options if row.get("provider") == target_provider), None)
	if not selected:
		frappe.throw(_("The selected provider is not available for the remaining appointment time."))

	old_provider = appointment.appointment_provider
	old_provider_name = (
		appointment.service_provider_name
		or frappe.db.get_value("Service Provider", old_provider, "provider_name")
		or old_provider
	)
	new_provider_name = selected.get("provider_name") or target_provider

	savepoint = f"ongoing_provider_handover_{appointment.name.replace('-', '_')}"
	frappe.db.savepoint(savepoint)

	try:
		allocation_names = _get_active_provider_allocations(appointment.name, old_provider)
		released_count = release_capacity_for_allocations(
			allocation_names=allocation_names,
			target_status="Released",
		)

		new_allocations = reserve_and_create_allocations(
			appointment_name=appointment.name,
			booking_name=appointment.booking_id,
			allocations=[
				{
					"resource_type": "Service Provider",
					"resource_reference": target_provider,
					"allocation_date": appointment.appointment_date,
					"start_time": handover.strftime("%H:%M:%S"),
					"end_time": _time_str(appointment.end_time),
					"appointment_start_time": handover.strftime("%H:%M:%S"),
					"appointment_end_time": _time_str(appointment.end_time),
					"capacity_consumed": 1.0,
					"buffer_before_minutes": 0,
					"buffer_after_minutes": 0,
				}
			],
			allocation_status="Confirmed",
			extra_metadata={
				"ongoing_provider_handover": True,
				"from_provider": old_provider,
				"to_provider": target_provider,
				"handover_time": handover.strftime("%H:%M:%S"),
			},
		)

		frappe.db.set_value(
			"Service Appointment",
			appointment.name,
			{
				"appointment_provider": target_provider,
				"service_provider_name": new_provider_name,
				"selected_slot_ids": None,
			},
			update_modified=True,
		)

		try:
			log_appointment_event(
				appointment.name,
				event_type="Provider Handover",
				old_value={"provider": old_provider, "provider_name": old_provider_name},
				new_value={
					"provider": target_provider,
					"provider_name": new_provider_name,
					"handover_time": handover.strftime("%H:%M:%S"),
				},
				notes=reason,
			)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				_("Failed to log provider handover for {0}").format(appointment.name),
			)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise

	return {
		"success": True,
		"message": _("Appointment provider handed over successfully."),
		"appointment": appointment.name,
		"handover_time": handover.strftime("%H:%M:%S"),
		"previous_provider": old_provider,
		"previous_provider_name": old_provider_name,
		"current_provider": target_provider,
		"provider_name": new_provider_name,
		"released_allocations": released_count,
		"new_allocations": new_allocations,
	}


def _get_replacement_options(appointment, handover: time) -> list[dict[str, Any]]:
	_assert_ongoing_appointment(appointment)
	if not appointment.appointment_provider:
		frappe.throw(_("Current provider is required before handover."))

	provider_ids = _get_service_providers(
		appointment.appointment_type, exclude=appointment.appointment_provider
	)
	options = []
	for provider in provider_ids:
		if not _provider_available_for_interval(
			provider=provider,
			appointment_date=appointment.appointment_date,
			start_time=handover,
			end_time=appointment.end_time,
		):
			continue

		provider_name = frappe.db.get_value("Service Provider", provider, "provider_name") or provider
		options.append(
			{
				"provider": provider,
				"provider_name": provider_name,
				"service_unit": appointment.service_unit,
				"service_unit_name": (
					frappe.db.get_value("Service Unit", appointment.service_unit, "unit_name")
					if appointment.service_unit
					else None
				),
				"handover_time": handover.strftime("%H:%M:%S"),
			}
		)

	return rank_provider_options(
		options,
		appointment_date=appointment.appointment_date,
		service_type=appointment.appointment_type,
		exclude_provider=appointment.appointment_provider,
	)


def _get_service_providers(service_type: str, exclude: str | None = None) -> list[str]:
	if not service_type:
		return []

	rows = frappe.db.sql(
		"""
		SELECT DISTINCT sps.parent
		FROM `tabService Provider Service` sps
		INNER JOIN `tabService Provider` sp ON sp.name = sps.parent
		WHERE sps.service_type = %(service_type)s
		  AND sps.disabled = 0
		  AND sp.active = 1
		  AND (%(exclude)s IS NULL OR sp.name != %(exclude)s)
		""",
		{"service_type": service_type, "exclude": exclude},
		as_dict=True,
	)
	return [row["parent"] for row in rows]


def _provider_available_for_interval(provider: str, appointment_date, start_time, end_time) -> bool:
	target_date = getdate(appointment_date)
	rebuild_counter_for_date(
		counter_date=target_date,
		resource_type="Service Provider",
		resource_reference=provider,
	)

	slot_size = _slot_size_minutes()
	slot_times = _slot_times_for_interval(target_date, start_time, end_time, slot_size)
	if not slot_times:
		return False

	rows = frappe.get_all(
		"Resource Availability Counter",
		filters={
			"counter_date": target_date,
			"counter_slot_time": ["in", slot_times],
			"resource_type": "Service Provider",
			"resource_reference": provider,
		},
		fields=["counter_slot_time", "remaining_capacity", "is_blocked"],
	)
	by_slot = {_time_str(row.counter_slot_time): row for row in rows}
	for slot_time in slot_times:
		row = by_slot.get(slot_time)
		if not row:
			return False
		if cint(row.get("is_blocked") or 0):
			return False
		if flt(row.get("remaining_capacity") or 0) <= 0:
			return False

	return True


def _get_active_provider_allocations(appointment_name: str, provider: str) -> list[str]:
	if not frappe.db.exists("DocType", "Service Resource Allocation"):
		return []

	return frappe.get_all(
		"Service Resource Allocation",
		filters={
			"service_appointment": appointment_name,
			"resource_type": "Service Provider",
			"resource_reference": provider,
			"allocation_status": ["in", ACTIVE_ALLOCATION_STATUSES],
		},
		pluck="name",
	)


def _resolve_handover_time(appointment, handover_time: str | None = None) -> time:
	_assert_ongoing_appointment(appointment)
	start_dt = get_datetime(f"{appointment.appointment_date} {_time_str(appointment.start_time)}")
	end_dt = get_datetime(f"{appointment.appointment_date} {_time_str(appointment.end_time)}")
	if end_dt <= start_dt:
		end_dt = end_dt + timedelta(days=1)

	if handover_time:
		handover_dt = get_datetime(f"{appointment.appointment_date} {_time_str(handover_time)}")
	else:
		handover_dt = now_datetime()
		if handover_dt < start_dt:
			handover_dt = start_dt

	if handover_dt < start_dt:
		handover_dt = start_dt
	if handover_dt >= end_dt:
		frappe.throw(_("The appointment has no remaining time for provider handover."))

	return handover_dt.time().replace(microsecond=0)


def _assert_ongoing_appointment(appointment) -> None:
	if appointment.status not in ONGOING_STATUSES:
		frappe.throw(_("Only checked-in or in-progress appointments can use provider handover."))
	if appointment.docstatus == 2:
		frappe.throw(_("Cancelled appointments cannot be reassigned."))
	if not appointment.appointment_date or not appointment.start_time or not appointment.end_time:
		frappe.throw(_("Appointment date and time are required for provider handover."))


def _assert_can_write_appointment(appointment_name: str) -> None:
	if not appointment_name:
		frappe.throw(_("Appointment is required."))
	if not frappe.has_permission("Service Appointment", "write", appointment_name):
		frappe.throw(_("You do not have permission to update this appointment."), frappe.PermissionError)


def _slot_times_for_interval(allocation_date, start_time_value, end_time_value, slot_size: int) -> list[str]:
	start_dt = datetime.combine(allocation_date, get_time(start_time_value))
	end_dt = datetime.combine(allocation_date, get_time(end_time_value))
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


def _slot_size_minutes() -> int:
	return max(1, cint(frappe.db.get_single_value("Service Appointment Settings", "default_slot_size") or 15))


def _time_str(value) -> str:
	return get_time(value).strftime("%H:%M:%S")
