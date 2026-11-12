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
	"""Classifies every folio line for accounting and reporting (design §10.6).

	A Revenue or Allowance code covers an Item Group: staff post any Item of that group (or of its
	sub-groups) and the posting service finds this code (plan F7). A code may instead name a fixed
	Item, for charges that are always the same thing (ROOM, NOSHOW).
	"""

	def before_naming(self):
		self.code = normalize_code(self.code, "Code")

	def validate(self):
		self.code = normalize_code(self.code, "Code")
		if self.transaction_type in PAYMENT_TYPES:
			if not self.mode_of_payment:
				frappe.throw(_("{0} charge codes need a Mode of Payment.").format(_(self.transaction_type)))
			self.item = None
			self.item_group = None
		else:
			self.mode_of_payment = None
		if self.transaction_type != "Revenue":
			self.is_room_revenue = 0
		self.validate_item()
		self.validate_coverage_is_unique()
		self.validate_income_accounts()

	def validate_item(self):
		if self.item:
			item = frappe.db.get_value("Item", self.item, ["item_group", "disabled"], as_dict=True)
			if item.disabled:
				frappe.throw(_("Item {0} is disabled.").format(self.item))
			if not self.item_group:
				self.item_group = item.item_group
			elif not is_in_group(item.item_group, self.item_group):
				frappe.throw(
					_("Fixed Item {0} is in Item Group {1}, which is not part of {2}.").format(
						self.item, item.item_group, self.item_group
					)
				)
		if self.transaction_type not in ITEM_TYPES and not self.item:
			# Only Revenue and Allowance codes cover a group; the others group by transaction type.
			self.item_group = None
		elif self.transaction_type in ITEM_TYPES and not self.item_group:
			frappe.throw(
				_("{0} charge codes need an Item Group to cover, or a fixed Item.").format(
					_(self.transaction_type)
				)
			)

	def validate_coverage_is_unique(self):
		"""Posting must find exactly one code for an Item, so two active codes can't claim the same."""
		if not self.is_active or self.transaction_type not in ITEM_TYPES:
			return
		filters = {
			"is_active": 1,
			"transaction_type": self.transaction_type,
			"name": ["!=", self.name or ""],
		}
		if self.item:
			filters["item"] = self.item
			message = _("Charge code {0} already posts Item {1}.")
			value = self.item
		else:
			filters.update({"item_group": self.item_group, "item": ["is", "not set"]})
			message = _("Charge code {0} already covers Item Group {1}.")
			value = self.item_group
		other = frappe.db.get_value("Charge Code", filters, "name")
		if other:
			frappe.throw(message.format(other, value))

	def validate_income_accounts(self):
		"""Settlement invoices these Items for every hotel company, so each needs an income account."""
		if self.transaction_type not in ITEM_TYPES:
			return
		companies = frappe.get_all("Hotel Property", filters={"is_active": 1}, pluck="company", distinct=True)
		if self.item:
			missing = [company for company in companies if not income_account(self.item, company)]
			subject = _("Item {0}").format(self.item)
		else:
			missing = [company for company in companies if not group_income_account(self.item_group, company)]
			subject = _("Item Group {0}").format(self.item_group)
		if missing:
			frappe.throw(
				_(
					"{0} has no income account for {1}. Set one in the Item's or Item Group's defaults, or set the company's Default Income Account."
				).format(subject, ", ".join(missing))
			)


def is_in_group(item_group: str, ancestor: str) -> bool:
	"""True if `item_group` is `ancestor` or one of its sub-groups."""
	if item_group == ancestor:
		return True
	child = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=True)
	parent = frappe.db.get_value("Item Group", ancestor, ["lft", "rgt"], as_dict=True)
	return bool(child and parent and parent.lft <= child.lft and child.rgt <= parent.rgt)


def income_account(item: str, company: str) -> str | None:
	"""The income account ERPNext will use for `item` in `company` (same order as get_item_details)."""
	return (
		get_item_defaults(item, company).get("income_account")
		or get_item_group_defaults(item, company).get("income_account")
		or get_brand_defaults(item, company).get("income_account")
		or frappe.get_cached_value("Company", company, "default_income_account")
	)


def group_income_account(item_group: str, company: str) -> str | None:
	"""The income account an Item of `item_group` gets in `company` when the Item sets none itself."""
	account = frappe.db.get_value(
		"Item Default",
		{"parenttype": "Item Group", "parent": item_group, "company": company},
		"income_account",
	)
	return account or frappe.get_cached_value("Company", company, "default_income_account")
