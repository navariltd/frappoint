# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ServiceAppointmentPayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappoint.frappoint.doctype.service_appointment_payment_reference.service_appointment_payment_reference import (
			ServiceAppointmentPaymentReference,
		)

		amended_from: DF.Link | None
		amount: DF.Currency
		currency: DF.Link | None
		mode_of_payment: DF.Link
		name: DF.Int | None
		order_id: DF.Data | None
		payment_gateway: DF.Link | None
		payment_id: DF.Data | None
		payment_received: DF.Check
		posting_date: DF.Date | None
		reference_date: DF.Date | None
		reference_docname: DF.DynamicLink
		reference_doctype: DF.Link
		references: DF.Table[ServiceAppointmentPaymentReference]
		user: DF.Link | None
	# end: auto-generated types
	pass
