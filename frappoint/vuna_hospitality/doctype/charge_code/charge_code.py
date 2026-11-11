# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults
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
		if not self.item:
			self.item_group = None
		self.validate_income_accounts()

	def validate_income_accounts(self):
		"""Settlement invoices this Item for every hotel company, so each needs an income account."""
		if self.transaction_type not in ITEM_TYPES or not self.item:
			return
		companies = frappe.get_all("Hotel Property", filters={"is_active": 1}, pluck="company", distinct=True)
		missing = [company for company in companies if not income_account(self.item, company)]
		if missing:
			frappe.throw(
				_(
					"Item {0} has no income account for {1}. Set one in the Item's or Item Group's defaults, or set the company's Default Income Account."
				).format(self.item, ", ".join(missing))
			)


def income_account(item: str, company: str) -> str | None:
	"""The income account ERPNext will use for `item` in `company` (same order as get_item_details)."""
	return (
		get_item_defaults(item, company).get("income_account")
		or get_item_group_defaults(item, company).get("income_account")
		or get_brand_defaults(item, company).get("income_account")
		or frappe.get_cached_value("Company", company, "default_income_account")
	)
