# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from frappoint.vuna_hospitality.services import restrictions


class RateRestrictionDay(Document):
	"""Stay rules for one night, for one rate plan or all, and one room type or all (design §10.3)."""

	def autoname(self):
		self.name = restrictions.row_name(
			self.property, self.rate_plan, self.room_type, self.restriction_date
		)

	def validate(self):
		for doctype, name in (("Rate Plan", self.rate_plan), ("Room Type", self.room_type)):
			if name and frappe.db.get_value(doctype, name, "property") != self.property:
				frappe.throw(_("{0} {1} belongs to another property.").format(_(doctype), name))
		if not self.is_new() and any(
			self.has_value_changed(field)
			for field in ("property", "rate_plan", "room_type", "restriction_date")
		):
			frappe.throw(_("Make a new restriction for another night, plan or room type."))
		if cint(self.max_stay) and cint(self.min_stay_arrival) > cint(self.max_stay):
			frappe.throw(_("The minimum stay can't be longer than the maximum stay."))
		if cint(self.max_advance_days) and cint(self.min_advance_days) > cint(self.max_advance_days):
			frappe.throw(_("Minimum days ahead can't be more than maximum days ahead."))
		if not restrictions.has_rules(self):
			frappe.throw(_("Set at least one rule, or delete the restriction."))
		self.restriction_summary = restrictions.summary(self)

	def on_update(self):
		restrictions.audit_change(self, "Restriction Saved")

	def on_trash(self):
		restrictions.audit_change(self, "Restriction Removed")
