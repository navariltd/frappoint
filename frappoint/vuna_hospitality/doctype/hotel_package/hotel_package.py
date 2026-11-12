# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from frappoint.vuna_hospitality.services.pricing_masters import (
	assert_allowance_covers,
	assert_fixed_revenue_code,
)
from frappoint.vuna_hospitality.services.rooms import normalize_code


class HotelPackage(Document):
	"""A rate plan's package: components split out of, or added to, each night (design §10.5)."""

	def autoname(self):
		# Codes are unique per property, so the record name carries both: e.g. "LKS-BB".
		self.package_code = normalize_code(self.package_code, "Code")
		self.name = f"{self.property}-{self.package_code}"

	def validate(self):
		self.package_code = normalize_code(self.package_code, "Code")
		if not self.components:
			frappe.throw(_("A package needs at least one component."))
		for component in self.components:
			label = _("Component {0}").format(component.component_name)
			code = assert_fixed_revenue_code(component.charge_code, label)
			if flt(component.amount) <= 0:
				frappe.throw(_("{0}: the amount must be more than zero.").format(label))
			if component.amount_type == "Percentage" and flt(component.amount) > 100:
				frappe.throw(_("{0}: a percentage can't exceed 100.").format(label))
			if component.amount_basis == "Per Stay":
				component.posting_rhythm = "Arrival Night"
			if component.is_allowance:
				assert_allowance_covers(component.allowance_charge_code, code.item, label)
				component.valid_days = max(component.valid_days or 1, 1)
			else:
				component.allowance_charge_code = None
