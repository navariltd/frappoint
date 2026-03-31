# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


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

	def validate(self):
		if self.reference_doctype not in ["Service Booking", "Service Appointment"]:
			frappe.throw("Not Supported")

		if self.references:
			for reference in self.references:
				if reference.reference_doctype not in ["Service Appointment"]:
					frappe.throw("Not Supported")

		if self.reference_doctype and self.reference_docname and not self.amount:
			self.get_reference_details()

		# If paying for a Booking but references table is empty, populate it
		if self.reference_doctype == "Service Booking" and not self.references:
			self.get_references()

	def on_submit(self):
		self.update_outstanding_balances(cancel=False)

	def on_cancel(self):
		self.update_outstanding_balances(cancel=True)

	def update_outstanding_balances(self, cancel=False):
		self.adjust_doc_outstanding(self.reference_doctype, self.reference_docname, self.amount, cancel)

		if self.reference_doctype == "Service Booking":
			for ref in self.references:
				self.adjust_doc_outstanding(
					ref.reference_doctype, ref.reference_name, ref.allocated_amount, cancel
				)

	def adjust_doc_outstanding(self, doctype, docname, amount, cancel):
		change = flt(amount) if cancel else -flt(amount)

		new_outstanding = flt(frappe.db.get_value(doctype, docname, "outstanding_amount")) + change

		frappe.db.set_value(doctype, docname, "outstanding_amount", new_outstanding)

	@frappe.whitelist()
	def get_reference_details(self):
		"""Fetch amount and currency from the source document"""
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_docname)
		self.currency = ref_doc.currency
		self.amount = ref_doc.outstanding_amount

	@frappe.whitelist()
	def get_references(self):
		"""Populate the child table with linked appointments"""
		if self.reference_doctype != "Service Booking":
			return

		self.set("references", [])

		appointments = frappe.get_all(
			"Service Appointment",
			filters={
				"booking_id": self.reference_docname,
				"status": ["not in", ["Cancelled"]],
				"outstanding_amount": [">", 0],
			},
			fields=["name", "grand_total", "outstanding_amount", "currency"],
		)

		for appt in appointments:
			self.append(
				"references",
				{
					"reference_doctype": "Service Appointment",
					"reference_name": appt.name,
					"currency": appt.currency,
					"grand_total": appt.grand_total,
					"outstanding_amount": appt.outstanding_amount,
					"allocated_amount": appt.outstanding_amount,
				},
			)
