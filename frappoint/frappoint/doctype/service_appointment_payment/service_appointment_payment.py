# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.party import get_party_account
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


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
		payment_entry: DF.Link | None
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
		self.validate_allocation_sum()

		if self.reference_doctype not in ["Service Booking", "Service Appointment"]:
			frappe.throw(_("Not Supported"))

		if self.references:
			for reference in self.references:
				if reference.reference_doctype not in ["Service Appointment"]:
					frappe.throw(_("Not Supported"))

		if self.reference_doctype and self.reference_docname and not self.amount:
			self.get_reference_details()

		# If paying for a Booking but references table is empty, populate it
		if self.reference_doctype == "Service Booking" and not self.references:
			self.get_references()

	def on_submit(self):
		self.create_payment_entry()
		self.update_outstanding_balances(cancel=False)

	def on_cancel(self):
		self.cancel_payment_entry()
		self.update_outstanding_balances(cancel=True)

	def get_reference_doc(self):
		if not self.reference_doctype or not self.reference_docname:
			frappe.throw(_("Reference document is required."))

		return frappe.get_doc(self.reference_doctype, self.reference_docname)

	def get_company(self, reference_doc):
		company = reference_doc.get("company")
		if company:
			return company

		company = frappe.defaults.get_user_default("Company")
		if company:
			return company

		return frappe.db.get_single_value("Global Defaults", "default_company")

	def get_mode_of_payment_account(self, company):
		account = frappe.db.get_value(
			"Mode of Payment Account",
			{"parent": self.mode_of_payment, "company": company},
			"default_account",
		)

		if not account:
			frappe.throw(
				_("Mode of Payment {0} does not have a default account for company {1}.").format(
					self.mode_of_payment, company
				)
			)

		return account

	def create_payment_entry(self):
		if self.payment_entry:
			return self.payment_entry

		if flt(self.amount) <= 0:
			frappe.throw(_("Payment amount must be greater than zero."))

		reference_doc = self.get_reference_doc()
		customer = reference_doc.get("customer")
		if not customer:
			frappe.throw(_("Customer is required to create a Payment Entry."))

		company = self.get_company(reference_doc)
		if not company:
			frappe.throw(_("Default company is required to create a Payment Entry."))

		paid_to = self.get_mode_of_payment_account(company)
		paid_from = get_party_account("Customer", customer, company)

		payment_entry = frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"payment_type": "Receive",
				"company": company,
				"posting_date": self.posting_date or today(),
				"mode_of_payment": self.mode_of_payment,
				"party_type": "Customer",
				"party": customer,
				"paid_from": paid_from,
				"paid_to": paid_to,
				"paid_amount": flt(self.amount),
				"received_amount": flt(self.amount),
				"reference_no": str(self.payment_id or self.order_id or self.name),
				"reference_date": self.reference_date or self.posting_date or today(),
				"remarks": _("Advance payment for {0} {1}").format(
					self.reference_doctype, self.reference_docname
				),
			}
		)
		payment_entry.insert(ignore_permissions=True, ignore_mandatory=True)
		payment_entry.submit()

		self.db_set("payment_entry", payment_entry.name, update_modified=False)
		self.payment_entry = payment_entry.name
		return payment_entry.name

	def cancel_payment_entry(self):
		if not self.payment_entry:
			return

		if not frappe.db.exists("Payment Entry", self.payment_entry):
			return

		payment_entry = frappe.get_doc("Payment Entry", self.payment_entry)
		if payment_entry.docstatus == 1:
			payment_entry.cancel()

	def update_outstanding_balances(self, cancel=False):
		self.adjust_doc_outstanding(self.reference_doctype, self.reference_docname, self.amount, cancel)

		booking_to_attempt_submit = None

		if self.reference_doctype == "Service Appointment":
			appt_doc = frappe.get_doc("Service Appointment", self.reference_docname, ignore_permissions=True)

			appt_doc.update_payment_and_workflow_status()

			parent_booking = frappe.db.get_value("Service Appointment", self.reference_docname, "booking_id")
			if parent_booking:
				self.adjust_doc_outstanding("Service Booking", parent_booking, self.amount, cancel)
				booking_doc = frappe.get_doc("Service Booking", parent_booking, ignore_permissions=True)
				booking_doc.sync_financial_snapshot()
				booking_to_attempt_submit = parent_booking

		if self.reference_doctype == "Service Booking":
			booking_doc = frappe.get_doc("Service Booking", self.reference_docname, ignore_permissions=True)
			booking_doc.sync_financial_snapshot()
			booking_to_attempt_submit = self.reference_docname

			for ref in self.references:
				self.adjust_doc_outstanding(
					ref.reference_doctype, ref.reference_name, ref.allocated_amount, cancel
				)

				if ref.reference_doctype == "Service Appointment":
					appt_doc = frappe.get_doc(
						"Service Appointment", ref.reference_name, ignore_permissions=True
					)
					appt_doc.recalculate_outstanding_from_payments()
					appt_doc.update_payment_and_workflow_status()

		if booking_to_attempt_submit and not cancel:
			try:
				booking_doc = frappe.get_doc(
					"Service Booking", booking_to_attempt_submit, ignore_permissions=True
				)
				booking_doc.maybe_auto_submit_after_payment()
			except Exception:
				frappe.log_error(
					frappe.get_traceback(),
					_("Failed to auto-submit booking {0}").format(booking_to_attempt_submit),
				)

	def adjust_doc_outstanding(self, doctype, docname, amount, cancel):
		change = flt(amount) if cancel else -flt(amount)

		new_outstanding = flt(frappe.db.get_value(doctype, docname, "outstanding_amount")) + change

		frappe.db.set_value(doctype, docname, "outstanding_amount", new_outstanding)

	def validate_allocation_sum(self):
		"""
		Ensures the 'amount' (total paid) matches the sum of
		individual allocations in the child table.
		"""
		if not self.references:
			return

		total_allocated = 0
		for d in self.references:
			total_allocated += flt(d.allocated_amount)

		if abs(flt(self.amount) - total_allocated) > 0.01:
			frappe.throw(
				_("Total Allocated Amount ({0}) must be equal to the Payment Amount ({1})").format(
					frappe.format(total_allocated, "Currency", self.currency),
					frappe.format(self.amount, "Currency", self.currency),
				),
				title=_("Allocation Mismatch"),
			)

	@frappe.whitelist()
	def get_reference_details(self):
		"""Fetch amount and currency from the source document"""
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_docname)
		self.currency = ref_doc.currency
		self.amount = ref_doc.outstanding_amount

	@frappe.whitelist()
	def get_references(self):
		"""
		Populate the child table with linked appointments using proportional allocation.
		Allocates payment proportionally based on each appointment's confirmation deposit requirement.
		"""
		if self.reference_doctype != "Service Booking":
			return

		self.set("references", [])

		appointments = frappe.get_all(
			"Service Appointment",
			filters={
				"booking_id": self.reference_docname,
				"status": ["not in", ["Cancelled", "Rescheduled", "Closed"]],
				"outstanding_amount": [">", 0],
			},
			fields=[
				"name",
				"grand_total",
				"outstanding_amount",
				"confirmation_required_amount",
				"currency",
			],
		)

		if not appointments:
			return

		payment_amount = flt(self.amount)

		# Calculate total deposit required across all active appointments
		total_deposit_required = sum(
			flt(appt.get("confirmation_required_amount", 0)) for appt in appointments
		)

		# Allocate payment proportionally based on each appointment's deposit requirement
		for appt in appointments:
			deposit_required = flt(appt.get("confirmation_required_amount", 0))
			outstanding = flt(appt.get("outstanding_amount", 0))

			# Calculate this appointment's allocation share
			if total_deposit_required > 0:
				# Proportional to deposit requirement
				allocation_ratio = deposit_required / total_deposit_required
				allocated_amount = payment_amount * allocation_ratio
			else:
				# Fallback: allocate proportionally by outstanding amount if no deposits required
				total_outstanding = sum(flt(a.get("outstanding_amount", 0)) for a in appointments)
				if total_outstanding > 0:
					allocation_ratio = outstanding / total_outstanding
					allocated_amount = payment_amount * allocation_ratio
				else:
					allocated_amount = 0

			# Cap allocation to outstanding amount (cannot allocate more than owed)
			allocated_amount = min(allocated_amount, outstanding)

			if allocated_amount > 0.01:  # Only add if meaningful amount
				self.append(
					"references",
					{
						"reference_doctype": "Service Appointment",
						"reference_name": appt.name,
						"currency": appt.currency,
						"grand_total": appt.grand_total,
						"outstanding_amount": outstanding,
						"allocated_amount": allocated_amount,
					},
				)
