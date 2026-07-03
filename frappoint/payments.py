import frappe
from frappe import _
from frappe.utils import flt
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


def _resolve_mode_of_payment_for_gateway(payment_gateway, currency=None):
	if not payment_gateway:
		return None

	# Common convention in ERPNext gateway setup: Mode of Payment name equals gateway label.
	if frappe.db.exists("Mode of Payment", payment_gateway):
		enabled = frappe.db.get_value("Mode of Payment", payment_gateway, "enabled")
		if enabled or enabled is None:
			return payment_gateway

	# Prefer a mode that maps to the same account used by Payment Gateway Account.
	gateway_accounts = frappe.get_all(
		"Payment Gateway Account",
		filters={"payment_gateway": payment_gateway},
		fields=["payment_account", "currency", "is_default"],
	)

	if currency:
		matched = [row for row in gateway_accounts if row.get("currency") == currency]
		if matched:
			gateway_accounts = matched

	if gateway_accounts:
		gateway_accounts.sort(key=lambda row: int(bool(row.get("is_default"))), reverse=True)
		payment_account = gateway_accounts[0].get("payment_account")
		if payment_account:
			mop_accounts = frappe.get_all(
				"Mode of Payment Account",
				filters={"default_account": payment_account},
				fields=["parent"],
			)
			for row in mop_accounts:
				mode = row.get("parent")
				if not mode:
					continue
				enabled = frappe.db.get_value("Mode of Payment", mode, "enabled")
				if enabled or enabled is None:
					return mode

	# Some gateway controllers may explicitly define mode_of_payment.
	gateway_doc = frappe.db.get_value(
		"Payment Gateway",
		payment_gateway,
		["gateway_settings", "gateway_controller"],
		as_dict=True,
	)
	if gateway_doc and gateway_doc.gateway_settings and gateway_doc.gateway_controller:
		try:
			controller_doc = frappe.get_doc(
				gateway_doc.gateway_settings,
				gateway_doc.gateway_controller,
			)
			for fieldname in ("mode_of_payment", "payment_mode"):
				if controller_doc.meta.get_field(fieldname):
					mode = controller_doc.get(fieldname)
					if mode and frappe.db.exists("Mode of Payment", mode):
						return mode
		except Exception:
			pass

	# Last resort: a named mode that contains the gateway label.
	matching_modes = frappe.get_all(
		"Mode of Payment",
		filters={"enabled": 1, "name": ["like", f"%{payment_gateway}%"]},
		fields=["name"],
		order_by="name asc",
	)
	if matching_modes:
		return matching_modes[0].get("name")

	return None


def validate_currency(payment_gateway, currency):
	controller = get_controller(payment_gateway)
	controller.validate_transaction_currency(currency)


def get_confirmation_deposit_percent(reference_doctype, reference_docname, doc=None):
	settings = frappe.get_cached_doc("Service Appointment Settings")

	if not settings.enable_partial_confirmation:
		return 100

	default_percent = flt(settings.default_confirmation_deposit_percent) or 100

	if reference_doctype == "Service Appointment":
		if not doc:
			doc = frappe.get_cached_doc(reference_doctype, reference_docname)
		service_percent = flt(
			frappe.db.get_value("Service Type", doc.appointment_type, "confirmation_deposit_percent")
		)
		return service_percent if service_percent > 0 else default_percent

	if reference_doctype == "Service Booking":
		service_types = set()
		if doc and doc.items:
			service_types.update(row.service_type for row in doc.items if row.service_type)

		if not service_types:
			linked_appts = frappe.get_all(
				"Service Appointment",
				filters={"booking_id": reference_docname},
				pluck="appointment_type",
			)
			service_types.update(s for s in linked_appts if s)

		overrides = []
		for service_type in service_types:
			percent = flt(frappe.db.get_value("Service Type", service_type, "confirmation_deposit_percent"))
			if percent > 0:
				overrides.append(percent)

		return max(overrides) if overrides else default_percent

	return default_percent


def get_paid_amount(reference_doctype, reference_docname, total_amount, doc=None):
	if doc:
		outstanding = flt(doc.outstanding_amount)
	else:
		outstanding = flt(
			frappe.db.get_value(reference_doctype, reference_docname, "outstanding_amount") or total_amount
		)

	return max(0, flt(total_amount) - outstanding)


def get_payment_amount(reference_doctype, reference_docname, total_amount, doc=None):
	deposit_percent = get_confirmation_deposit_percent(reference_doctype, reference_docname, doc=doc)
	required_to_confirm = (flt(total_amount) * flt(deposit_percent)) / 100
	paid_amount = get_paid_amount(reference_doctype, reference_docname, total_amount, doc=doc)

	minimum_due = max(0, flt(required_to_confirm) - flt(paid_amount))
	remaining_due = max(0, flt(total_amount) - flt(paid_amount))

	return minimum_due if minimum_due > 0 else remaining_due


@frappe.whitelist()
def get_payment_link(
	reference_doctype: str,
	reference_docname: str,
	payment_gateway: str,
	redirect_to: str,
	amount: float | None = None,
	payment_type: str | None = None,
	coupon_code: str | None = None,
):
	"""
	Handles both Service Booking and Service Appointment
	"""
	requested_amount = flt(amount) if amount is not None else 0
	normalized_payment_type = (payment_type or "").strip().lower()
	doc = frappe.get_cached_doc(reference_doctype, reference_docname)

	if reference_doctype == "Service Booking":
		total_reference_amount = doc.final_amount or doc.grand_total
		currency = doc.currency
		customer = doc.customer
		mobile_no = doc.mobile_no
		service_type = None

	elif reference_doctype == "Service Appointment":
		total_reference_amount = doc.total_amount
		currency = doc.currency
		customer = doc.customer
		service_type = doc.appointment_type
		mobile_no = doc.mobile_no

	if not payment_gateway:
		if reference_doctype == "Service Appointment":
			gateways = get_payment_gateways_for_service_type(service_type)
		else:
			gateways = frappe.get_all(
				"Service Type Payment Gateway",
				filters={"parenttype": "Service Appointment Settings"},
				pluck="payment_gateway",
			)

		if not gateways:
			frappe.throw(_("No payment gateway configured for this service type"))

		payment_gateway = gateways[0]

	total_amount = flt(total_reference_amount)
	minimum_due = get_payment_amount(reference_doctype, reference_docname, total_amount, doc=doc)
	paid_amount = get_paid_amount(reference_doctype, reference_docname, total_amount, doc=doc)
	remaining_due = max(0, flt(total_amount) - flt(paid_amount))

	if normalized_payment_type == "full":
		amount_to_pay = remaining_due
	elif normalized_payment_type == "deposit":
		amount_to_pay = requested_amount if requested_amount > 0 else minimum_due
	else:
		if requested_amount > 0:
			amount_to_pay = requested_amount
		else:
			amount_to_pay = minimum_due

	if amount_to_pay < flt(minimum_due):
		frappe.throw(
			_("Selected payment amount cannot be less than the required minimum due of {0}.").format(
				minimum_due
			)
		)

	if amount_to_pay > flt(remaining_due):
		frappe.throw(
			_("Selected payment amount cannot exceed the outstanding balance of {0}.").format(remaining_due)
		)

	frappe.logger("frappoint.checkout").info(
		{
			"event": "get_payment_link_amount_resolution",
			"reference_doctype": reference_doctype,
			"reference_docname": reference_docname,
			"payment_type": normalized_payment_type,
			"coupon_code": coupon_code,
			"requested_amount": requested_amount,
			"minimum_due": minimum_due,
			"remaining_due": remaining_due,
			"amount_to_pay": amount_to_pay,
		}
	)

	if flt(amount_to_pay) <= 0:
		frappe.throw("No amount is due for this payment request")

	validate_currency(payment_gateway, currency)

	payment = record_payment(
		reference_doctype,
		reference_docname,
		amount_to_pay,
		currency,
		payment_gateway=payment_gateway,
	)
	controller = get_controller(payment_gateway)

	redirect_to = redirect_to

	payment_details = {
		"amount": amount_to_pay,
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


def record_payment(reference_doctype, reference_docname, amount, currency, payment_gateway=None):
	mode_of_payment = _resolve_mode_of_payment_for_gateway(payment_gateway, currency=currency)
	if not mode_of_payment:
		frappe.throw(
			_(
				"Could not determine Mode of Payment for gateway {0}. Configure a matching Mode of Payment or Payment Gateway Account mapping."
			).format(payment_gateway or _("Unknown"))
		)

	payment_doc = frappe.new_doc("Service Appointment Payment")
	payment_doc.update(
		{
			"user": frappe.session.user,
			"amount": amount,
			"currency": currency,
			"mode_of_payment": mode_of_payment,
			"payment_gateway": payment_gateway,
			"reference_doctype": reference_doctype,
			"reference_docname": reference_docname,
		}
	)

	payment_doc.save(ignore_permissions=True)

	if reference_doctype == "Service Appointment":
		appointment_status = frappe.db.get_value("Service Appointment", reference_docname, "status")
		if appointment_status in ["Open", "Pending Payment"]:
			frappe.db.set_value(
				"Service Appointment",
				reference_docname,
				{"status": "Pending Payment"},
			)

	if reference_doctype == "Service Booking":
		appointments = frappe.get_all(
			"Service Appointment",
			filters={
				"booking_id": reference_docname,
				"status": ["in", ["Open", "Pending Payment"]],
				"outstanding_amount": [">", 0],
				"docstatus": ["<", 2],
			},
			pluck="name",
		)

		for appointment_name in appointments:
			frappe.db.set_value(
				"Service Appointment",
				appointment_name,
				{"status": "Pending Payment"},
			)

		frappe.db.set_value(
			"Service Booking",
			reference_docname,
			{"status": "Payment Pending"},
		)

	return payment_doc
