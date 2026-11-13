# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services.rooms import normalize_code


class RatePlan(Document):
	"""A commercial room offering; its prices live in Room Rate Day (design §10.2)."""

	def autoname(self):
		# Codes are unique per property, so the record name carries both: e.g. "LKS-BAR".
		self.rate_plan_code = normalize_code(self.rate_plan_code, "Code")
		self.name = f"{self.property}-{self.rate_plan_code}"

	def validate(self):
		self.rate_plan_code = normalize_code(self.rate_plan_code, "Code")
		self.validate_room_charge_code()
		self.validate_package()
		self.validate_policy(self.cancellation_policy, "Cancellation")
		self.validate_policy(self.deposit_policy, "Deposit")
		if self.no_show_policy:
			self.validate_policy(self.no_show_policy, "No-show")
		if self.early_departure_policy:
			self.validate_policy(self.early_departure_policy, "Early Departure")

	def validate_room_charge_code(self):
		code = frappe.db.get_value(
			"Charge Code", self.room_charge_code, ["transaction_type", "is_active", "item"], as_dict=True
		)
		if code.transaction_type != "Revenue" or not code.is_active:
			frappe.throw(
				_("Room Charge Code {0} must be an active Revenue charge code.").format(self.room_charge_code)
			)
		if not code.item:
			# Night audit posts the room night without anyone picking an Item.
			frappe.throw(
				_("Room Charge Code {0} needs a fixed Item, because night audit posts it on its own.").format(
					self.room_charge_code
				)
			)

	def validate_package(self):
		if not self.package:
			return
		package = frappe.db.get_value("Hotel Package", self.package, ["property", "is_active"], as_dict=True)
		if package.property != self.property:
			frappe.throw(_("Package {0} belongs to another property.").format(self.package))
		if not package.is_active:
			frappe.throw(_("Package {0} is inactive.").format(self.package))

	def validate_policy(self, policy, policy_type):
		row = frappe.db.get_value(
			"Hotel Policy", policy, ["property", "policy_type", "is_active"], as_dict=True
		)
		if row.property != self.property:
			frappe.throw(_("Policy {0} belongs to another property.").format(policy))
		if row.policy_type != policy_type:
			frappe.throw(
				_("Policy {0} is a {1} policy, not a {2} policy.").format(
					policy, _(row.policy_type), _(policy_type)
				)
			)
		if not row.is_active:
			frappe.throw(_("Policy {0} is inactive.").format(policy))

	def on_trash(self):
		frappe.db.delete("Room Rate Day", {"rate_plan": self.name})
