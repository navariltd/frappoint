import frappe


def execute():
	"""Set default values for Service Appointment Settings if not already set."""

	if not frappe.db.exists("DocType", "Service Appointment Settings"):
		return

	try:
		doc = frappe.get_doc("Service Appointment Settings")

		if not doc.default_slot_size:
			doc.default_slot_size = 10

		if not doc.max_advance_days:
			doc.max_advance_days = 30

		if not doc.payment_hold_minutes:
			doc.payment_hold_minutes = 10

		if is_app_installed("erpnext"):
			if doc.use_erpnext_pricing is None:
				doc.use_erpnext_pricing = 1

			if doc.auto_create_service_items is None:
				doc.auto_create_service_items = 1

		doc.save(ignore_permissions=True)

	except Exception as e:
		frappe.log_error(
			"Error Setting Frappoint defaults", f"Error setting Service Appointment Settings defaults: {e}"
		)


def is_app_installed(app_name: str) -> bool:
	return app_name in frappe.get_installed_apps()
