import frappe

frappe.utils.logger.set_log_level("INFO")
mpesa_hook_logger = frappe.logger("frappoint_mpesa_hook", allow_site=True, file_count=2)


def hook_mpesa_express_request(doc, method=None):
	mpesa_hook_logger.info(
		"Hook fired",
		extra={
			"mpesa_request": doc.name,
			"status": doc.status,
			"reference": f"{doc.reference_doctype}:{doc.reference_name}",
		},
	)

	if doc.status != "Completed":
		mpesa_hook_logger.info("Skipping: status not completed")
		return

	if doc.reference_doctype != "Service Appointment":
		mpesa_hook_logger.warning("Unsupported reference doctype", extra={"doctype": doc.reference_doctype})
		return

	try:
		sa_doc = frappe.get_doc(doc.reference_doctype, doc.reference_name, ignore_permissions=True)

		mpesa_hook_logger.info(
			"Loaded Service Appointment", extra={"appointment": sa_doc.name, "docstatus": sa_doc.docstatus}
		)

		if sa_doc.docstatus == 1:
			mpesa_hook_logger.info("Appointment already submitted")
			return

		mpesa_hook_logger.info("Authorizing payment on appointment")
		sa_doc.on_payment_authorized("Completed")

	except Exception:
		mpesa_hook_logger.error("MPESA hook failed", extra={"mpesa_request": doc.name}, exc_info=True)
		frappe.log_error(title="Mpesa Express Hook Failure", message=frappe.get_traceback())
