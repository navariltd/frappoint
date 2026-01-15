from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import add_to_date, get_time, getdate, nowtime


@frappe.whitelist(allow_guest=True)
def create_service_appointment(
	service_type,
	appointment_date,
	appointment_time,
	customer_name,
	customer_email,
	customer_mobile,
	provider,
	start_time,
	details=None,
):
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

	appointment.insert()
	appointment.submit()
	frappe.db.commit()

	return {
		"message": _("Service appointment created successfully."),
		"appointment_id": appointment.name,
	}


def calculate_end_time(start_time, duration):
	"""
	Calculate end time by adding duration (in minutes) to start time
	"""
	# Parse start_time (format: "HH:MM" or "HH:MM:SS")
	time_obj = datetime.strptime(str(start_time), "%H:%M:%S" if start_time.count(":") == 2 else "%H:%M")

	# Add duration
	end_time_obj = time_obj + timedelta(minutes=duration)

	# Return in HH:MM:SS format
	return end_time_obj.strftime("%H:%M:%S")


def get_default_price_list():
	return frappe.db.get_single_value("Service Settings", "default_price_list")


def get_default_company():
	return frappe.db.get_single_value("Global Defaults", "default_company")


def get_service_type_amount(service_type):
	"""
	Get the default amount for a service type
	Returns: The rate of the first active price
	"""
	service_doc = frappe.get_doc("Service Type", service_type)

	if not service_doc.prices:
		return 0

	return 0


def get_service_type_duration(service_type):
	"""
	Get the default duration for a service type
	Returns: The duration of the service type
	"""
	return frappe.db.get_value("Service Type", service_type, "default_duration_in_minutes")
