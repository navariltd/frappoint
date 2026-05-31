import json
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import add_to_date, get_time, getdate, nowtime

from frappoint.frappoint.services.appointment_state_service import (
	cancel_appointment,
	confirm_appointment_allocations,
	reschedule_appointment,
	transition_appointment_status,
)
from frappoint.frappoint.services.booking_transaction_service import reserve_and_create_allocations


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def create_service_appointment(
	service_type: str,
	appointment_date: str,
	appointment_time: str,
	customer_name: str,
	customer_email: str,
	customer_mobile: str,
	provider: str,
	start_time: str,
	details: str | None = None,
) -> dict:
	"""
	Create a new service appointment
	Use case: Booking form submission
	"""
	current_date = getdate()
	current_time = nowtime()
	company = get_default_company()
	total_amount = get_service_type_amount(service_type)
	duration = get_service_type_duration(service_type)
	end_time = calculate_end_time(start_time, duration)

	# Get service type details to check guest requirements
	service_type_doc = frappe.get_doc("Service Type", service_type)

	appointment = frappe.get_doc(
		{
			"doctype": "Service Appointment",
			"company": company,
			"appointment_type": service_type,  # Changed from service_type to appointment_type
			"scheduled_time": f"{current_date} {current_time}",
			"appointment_date": appointment_date,
			"appointment_price": "Full Price",
			"total_amount": total_amount,
			"full_name": customer_name,
			"customer": customer_name,
			"email": customer_email,
			"mobile_no": customer_mobile,
			"appointment_provider": provider,
			"start_time": start_time,
			"end_time": end_time,  # ✅ Now setting end_time
			"duration": duration,
			"details": details,
			"status": "Open",
			"source": "Portal",
			"payment_status": "Unpaid",
		}
	)

	if service_type_doc.min_guests == 1:
		appointment.append(
			"guests",
			{
				"full_name": customer_name,
				"email": customer_email,
				"mobile_no": customer_mobile,
				"is_primary": 1,
			},
		)

	appointment.insert()
	frappe.db.commit()

	return {
		"message": _("Service appointment created successfully."),
		"appointment_id": appointment.name,
	}


def calculate_end_time(start_time: str, duration: int) -> str:
	"""
	Calculate end time by adding duration (in minutes) to start time
	"""
	# Parse start_time (format: "HH:MM" or "HH:MM:SS")
	time_obj = datetime.strptime(str(start_time), "%H:%M:%S" if start_time.count(":") == 2 else "%H:%M")

	# Add duration
	end_time_obj = time_obj + timedelta(minutes=duration)

	# Return in HH:MM:SS format
	return end_time_obj.strftime("%H:%M:%S")


def get_default_price_list() -> str | None:
	return frappe.db.get_single_value("Service Settings", "default_price_list")


def get_default_company() -> str | None:
	return frappe.db.get_single_value("Global Defaults", "default_company")


def get_service_type_amount(service_type: str) -> float:
	"""
	Get the default amount for a service type
	Returns: The rate of the first active price
	"""
	service_doc = frappe.get_doc("Service Type", service_type)

	if not service_doc.prices:
		return 0

	return 0


def get_service_type_duration(service_type: str) -> int:
	"""
	Get the default duration for a service type
	Returns: The duration of the service type
	"""
	return frappe.db.get_value("Service Type", service_type, "default_duration_in_minutes")


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_cancellation_reasons() -> list[dict]:
	"""Get all active cancellation reasons"""
	reasons = frappe.get_all(
		"Service Appointment Lost Reason",
		fields=["lost_reason"],
		order_by="lost_reason asc",
	)

	return reasons


@frappe.whitelist()
def reserve_appointment_allocations(appointment_name: str, allocations, booking_name: str | None = None):
	"""Reserve capacity atomically and create resource allocations for an appointment."""
	if isinstance(allocations, str):
		allocations = json.loads(allocations)

	allocation_names = reserve_and_create_allocations(
		appointment_name=appointment_name,
		booking_name=booking_name,
		allocations=allocations,
		allocation_status="Held",
	)

	return {"appointment": appointment_name, "allocations": allocation_names}


@frappe.whitelist()
def confirm_allocations(appointment_name: str):
	"""Confirm held allocations and mark appointment confirmed where allowed."""
	return confirm_appointment_allocations(appointment_name)


@frappe.whitelist()
def change_appointment_status(appointment_name: str, to_status: str, reason: str | None = None):
	"""Validate and apply appointment status transition via state machine."""
	return transition_appointment_status(
		appointment_name=appointment_name, to_status=to_status, reason=reason
	)


@frappe.whitelist()
def cancel_appointment_with_release(appointment_name: str, reason: str | None = None):
	"""Cancel appointment and release resource allocations atomically."""
	return cancel_appointment(appointment_name=appointment_name, reason=reason)


@frappe.whitelist()
def reschedule_appointment_with_allocations(
	appointment_name: str,
	new_appointment_data,
	new_allocations,
	reason: str | None = None,
):
	"""Reschedule appointment while releasing/re-reserving resource allocations atomically."""
	if isinstance(new_appointment_data, str):
		new_appointment_data = json.loads(new_appointment_data)
	if isinstance(new_allocations, str):
		new_allocations = json.loads(new_allocations)

	return reschedule_appointment(
		appointment_name=appointment_name,
		new_appointment_data=new_appointment_data,
		new_allocations=new_allocations,
		reason=reason,
	)
