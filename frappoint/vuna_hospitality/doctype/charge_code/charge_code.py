# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services.rooms import normalize_code

ITEM_TYPES = ("Revenue", "Allowance")
PAYMENT_TYPES = ("Payment", "Deposit")


class ChargeCode(Document):
	"""Classifies every folio line for accounting and reporting (design §10.6)."""

	def before_naming(self):
		self.code = normalize_code(self.code, "Code")

	def validate(self):
		self.code = normalize_code(self.code, "Code")
		if self.transaction_type in ITEM_TYPES and not self.item:
			frappe.throw(
				_("{0} charge codes need an Item for the income account and tax.").format(
					_(self.transaction_type)
				)
			)
		if self.transaction_type in PAYMENT_TYPES:
			if not self.mode_of_payment:
				frappe.throw(_("{0} charge codes need a Mode of Payment.").format(_(self.transaction_type)))
			self.item = None
		else:
			self.mode_of_payment = None
		if self.transaction_type != "Revenue":
			self.is_room_revenue = 0
		if self.item and frappe.db.get_value("Item", self.item, "disabled"):
			frappe.throw(_("Item {0} is disabled.").format(self.item))
