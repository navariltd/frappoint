# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

VALUE_TYPES = ("Percentage of Stay", "Fixed Amount")


class HotelPolicy(Document):
	"""Cancellation, deposit, no-show or early-departure rules. Snapshotted onto stays when booked."""

	def validate(self):
		if self.policy_type == "Deposit":
			self.fee_type, self.fee_value, self.free_until_hours_before_arrival = "None", 0, 0
			self.validate_value(self.deposit_type, self.deposit_value, "Deposit Value")
		else:
			self.deposit_type, self.deposit_value = "None", 0
			if self.policy_type != "Cancellation":
				self.free_until_hours_before_arrival = 0
			self.validate_value(self.fee_type, self.fee_value, "Fee Value")

	def validate_value(self, kind, value, label):
		if kind not in VALUE_TYPES:
			return
		if flt(value) <= 0:
			frappe.throw(_("{0} must be more than 0.").format(_(label)))
		if kind == "Percentage of Stay" and flt(value) > 100:
			frappe.throw(_("{0} cannot be more than 100%.").format(_(label)))
