# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services.cashiering import SERVICE_FLAG


class FolioPaymentAllocation(Document):
	"""The part of a payment (or refund) that went to one folio (design §16.3). Never changed:
	moving money between folios is a refund and a new payment."""

	def validate(self):
		if not self.is_new() or not self.flags.get(SERVICE_FLAG):
			frappe.throw(_("Payment allocations are made by the cashier actions."), frappe.PermissionError)

	def on_update_after_submit(self):
		frappe.throw(_("Payment allocations can't be changed."), frappe.PermissionError)

	def before_cancel(self):
		frappe.throw(
			_("Payment allocations can't be cancelled. Refund the payment instead."), frappe.PermissionError
		)

	def on_trash(self):
		frappe.throw(_("Payment allocations can't be deleted."), frappe.PermissionError)
