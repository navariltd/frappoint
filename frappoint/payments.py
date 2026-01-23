import frappe
from payments.utils import get_payment_gateway_controller


def get_payment_gateway():
	return frappe.db.get_single_value("Service Appointment Settings", "payment_gateway")


def get_controller(payment_gateway):
	return get_payment_gateway_controller(payment_gateway)


def validate_currency(payment_gateway, currency):
	controller = get_controller(payment_gateway)
	controller().validate_transaction_currency(currency)


@frappe.whitelist()
def get_payment_link(service_appointment_id):
	payment_gateway = get_payment_gateway()
	service_appointment_doc = frappe.get_cached_doc("Service Appointment", service_appointment_id)
	service_type = service_appointment_doc.appointment_type
	user_full_name = service_appointment_doc.full_name
	amount = service_appointment_doc.total_amount
	currency = service_appointment_doc.currency

	validate_currency(payment_gateway, currency)

	payment = record_payment(
		service_appointment_id, service_appointment_doc.total_amount, service_appointment_doc.currency
	)
	controller = get_controller(payment_gateway)

	redirect_to = f"/portal/booking/{service_appointment_id}"

	payment_details = {
		"amount": amount,
		"title": f"Payment for: {service_type}",
		"description": f"{user_full_name}'s payment for {service_appointment_id}",
		"reference_doctype": "Service Appointment",
		"reference_docname": service_appointment_id,
		"payer_email": frappe.session.user,
		"payer_name": user_full_name,
		"currency": currency,
		"payment_gateway": payment_gateway,
		"redirect_to": redirect_to,
		"payment": payment.name,
	}

	url = controller.get_payment_url(**payment_details)

	return url


def record_payment(service_appointment, amount, currency):
	payment_doc = frappe.new_doc("Service Appointment Payment")
	payment_doc.update(
		{
			"user": frappe.session.user,
			"amount": amount,
			"currency": currency,
			"reference_doctype": "Service Appointment",
			"reference_docname": service_appointment,
		}
	)

	payment_doc.save(ignore_permissions=True)
	return payment_doc
