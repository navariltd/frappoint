import frappe

from ...frappoint.doctype.service_appointment.service_appointment import ServiceAppointment


def hook_integration_request(doc, method=None):
	if doc.status != "Completed":
		return

	if doc.reference_doctype != "Mpesa Express Request":
		return

	mpesa_doc = frappe.get_doc(doc.reference_doctype, doc.reference_docname, ignore_permissions=True)

	if mpesa_doc.status != "Completed" or mpesa_doc.result_code != "0":
		return

	if not mpesa_doc.reference_doctype or not mpesa_doc.reference_name:
		return

	sa_doc = frappe.get_doc(mpesa_doc.reference_doctype, mpesa_doc.reference_name, ignore_permissions=True)

	sa_doc.on_payment_authorized("Completed")
