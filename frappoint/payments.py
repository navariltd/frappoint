import frappe
from payments.utils import get_payment_gateway_controller


def get_payment_gateways_for_service_type(service_type):
	"""Get all payment gateways configured for a service type"""
	gateways = frappe.get_all(
		"Service Type Payment Gateway",
		filters={"parent": service_type, "parenttype": "Service Type"},
		pluck="payment_gateway",
	)

	if not gateways:
		gateways = frappe.get_all(
			"Service Type Payment Gateway",
			filters={"parenttype": "Service Appointment Settings"},
			pluck="payment_gateway",
		)
	return gateways


def get_controller(payment_gateway):
	return get_payment_gateway_controller(payment_gateway)


def validate_currency(payment_gateway, currency):
	controller = get_controller(payment_gateway)
	controller.validate_transaction_currency(currency)


@frappe.whitelist()
def get_payment_link(reference_doctype, reference_docname, payment_gateway, redirect_to):
	"""
	Handles both Service Booking and Service Appointment
	"""
	doc = frappe.get_cached_doc(reference_doctype, reference_docname)

	if reference_doctype == "Service Booking":
		amount = doc.grand_total
		currency = doc.currency
		customer = doc.customer
		mobile_no = doc.mobile_no

	elif reference_doctype == "Service Appointment":
		amount = doc.total_amount
		currency = doc.currency
		customer = doc.customer
		service_type = doc.appointment_type
		mobile_no = doc.mobile_no

	if not payment_gateway:
		gateways = get_payment_gateways_for_service_type(service_type)
		if not gateways:
			frappe.throw("No payment gateway configured for this service type")

	validate_currency(payment_gateway, currency)

	payment = record_payment(reference_doctype, reference_docname, amount, currency)
	controller = get_controller(payment_gateway)

	redirect_to = redirect_to

	payment_details = {
		"amount": amount,
		"title": f"Payment for: {reference_docname}",
		"description": f"Payment for {reference_doctype} {reference_docname}",
		"reference_doctype": reference_doctype,
		"reference_docname": reference_docname,
		"payer_email": frappe.session.user,
		"payer_name": customer,
		"currency": currency,
		"payment_gateway": payment_gateway,
		"redirect_to": redirect_to,
		"payment": payment.name,
	}

	if controller.doctype == "Mpesa Settings":
		payment_details["phone_number"] = mobile_no

	url = controller.get_payment_url(**payment_details)

	return url


def record_payment(reference_doctype, reference_docname, amount, currency):
	payment_doc = frappe.new_doc("Service Appointment Payment")
	payment_doc.update(
		{
			"user": frappe.session.user,
			"amount": amount,
			"currency": currency,
			"reference_doctype": reference_doctype,
			"reference_docname": reference_docname,
		}
	)

	payment_doc.save(ignore_permissions=True)
	return payment_doc
