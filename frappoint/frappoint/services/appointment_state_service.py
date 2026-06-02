from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime

from frappoint.frappoint.services.booking_transaction_service import (
	confirm_held_allocations,
	release_capacity_for_allocations,
	reserve_and_create_allocations,
)

ALLOWED_TRANSITIONS = {
	"Draft": {"Held", "Cancelled"},
	"Open": {"Pending Payment", "Confirmed", "Cancelled", "Rescheduled", "No Show"},
	"Pending Payment": {"Confirmed", "Cancelled", "Rescheduled", "No Show", "Open"},
	"Held": {"Confirmed", "Cancelled", "Expired"},
	"Confirmed": {"Checked In", "In Progress", "Cancelled", "Rescheduled", "No Show"},
	"Checked In": {"In Progress", "Paused", "Cancelled", "No Show"},
	"In Progress": {"Paused", "Completed", "Cancelled"},
	"Paused": {"In Progress", "Completed", "Cancelled"},
	"Completed": set(),
	"Cancelled": set(),
	"No Show": set(),
	"Rescheduled": {"Confirmed", "Cancelled"},
	"Expired": set(),
	"Closed": set(),
}


class InvalidAppointmentTransition(frappe.ValidationError):
	pass


def transition_appointment_status(
	appointment_name: str,
	to_status: str,
	reason: str | None = None,
	allow_noop: bool = True,
) -> dict[str, Any]:
	"""Validate and apply appointment lifecycle transition."""
	appointment = frappe.get_doc("Service Appointment", appointment_name)
	from_status = appointment.status

	if from_status == to_status:
		if allow_noop:
			return {"name": appointment_name, "from": from_status, "to": to_status, "changed": False}
		raise InvalidAppointmentTransition(_("Appointment already in status {0}").format(to_status))

	allowed = ALLOWED_TRANSITIONS.get(from_status, set())
	if to_status not in allowed:
		raise InvalidAppointmentTransition(
			_("Invalid transition from {0} to {1}").format(from_status, to_status)
		)

	appointment.db_set("status", to_status)
	if to_status == "Cancelled":
		appointment.db_set("cancellation_date", now_datetime())
		if reason:
			appointment.db_set("cancellation_notes", reason)

	log_appointment_event(
		appointment_name,
		event_type="Status Changed",
		old_value={"status": from_status},
		new_value={"status": to_status},
		notes=reason,
	)

	return {"name": appointment_name, "from": from_status, "to": to_status, "changed": True}


def cancel_appointment(appointment_name: str, reason: str | None = None) -> dict[str, Any]:
	"""Cancel appointment and release active resource allocations atomically."""
	appointment = frappe.get_doc("Service Appointment", appointment_name)
	from_status = appointment.status

	released_count = release_capacity_for_allocations(
		appointment_name=appointment_name,
		target_status="Cancelled",
	)
	appointment.db_set("status", "Cancelled")
	appointment.db_set("cancellation_date", now_datetime())
	if reason:
		appointment.db_set("cancellation_notes", reason)

	log_appointment_event(
		appointment_name,
		event_type="Cancelled",
		old_value={"status": from_status},
		new_value={"status": "Cancelled"},
		notes=reason,
	)

	return {"appointment": appointment_name, "released_allocations": released_count}


def reschedule_appointment(
	appointment_name: str,
	new_appointment_data: dict[str, Any],
	new_allocations: list[dict[str, Any]],
	reason: str | None = None,
) -> dict[str, Any]:
	"""Reschedule appointment by releasing old allocations and reserving new ones."""
	appointment = frappe.get_doc("Service Appointment", appointment_name)
	old_snapshot = {
		"appointment_date": appointment.appointment_date,
		"start_time": appointment.start_time,
		"end_time": appointment.end_time,
		"appointment_provider": appointment.appointment_provider,
		"service_unit": appointment.service_unit,
	}

	savepoint = f"reschedule_{appointment_name.replace('-', '_')}"
	frappe.db.savepoint(savepoint)

	try:
		release_capacity_for_allocations(appointment_name=appointment_name, target_status="Released")

		allocation_status = "Confirmed" if appointment.status == "Confirmed" else "Held"
		new_allocation_names = reserve_and_create_allocations(
			appointment_name=appointment_name,
			booking_name=appointment.booking_id,
			allocations=new_allocations,
			allocation_status=allocation_status,
			extra_metadata={"reschedule": True},
		)

		for key in ["appointment_date", "start_time", "end_time", "appointment_provider", "service_unit"]:
			if key in new_appointment_data:
				appointment.db_set(key, new_appointment_data[key])
		appointment.db_set("status", "Rescheduled")

		log_appointment_event(
			appointment_name,
			event_type="Rescheduled",
			old_value=old_snapshot,
			new_value=new_appointment_data,
			notes=reason,
		)

		return {
			"appointment": appointment_name,
			"new_allocations": new_allocation_names,
			"status": "Rescheduled",
		}
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def confirm_appointment_allocations(appointment_name: str) -> dict[str, Any]:
	"""Confirm held allocations and move appointment to Confirmed."""
	count = confirm_held_allocations(appointment_name)
	appointment = frappe.get_doc("Service Appointment", appointment_name)
	from_status = appointment.status
	if appointment.status in ("Open", "Pending Payment", "Held"):
		appointment.db_set("status", "Confirmed")

	log_appointment_event(
		appointment_name,
		event_type="Status Changed",
		old_value={"status": from_status},
		new_value={"status": "Confirmed"},
		notes="Allocations confirmed",
	)

	return {"appointment": appointment_name, "confirmed_allocations": count}


def log_appointment_event(
	appointment_name: str,
	event_type: str,
	old_value: dict[str, Any] | None = None,
	new_value: dict[str, Any] | None = None,
	notes: str | None = None,
) -> str | None:
	"""Log to v2 event table if present; no-op otherwise."""
	if not frappe.db.exists("DocType", "Service Appointment Event Log V2"):
		return None

	doc = frappe.get_doc(
		{
			"doctype": "Service Appointment Event Log V2",
			"appointment": appointment_name,
			"event_type": event_type,
			"old_value": old_value,
			"new_value": new_value,
			"notes": notes,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name
