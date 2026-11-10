# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, flt, getdate

MAX_SEASON_NIGHTS = 731


class RateSeason(Document):
	"""Date range and weekday/weekend prices used to generate Room Rate Days. Never read at booking time."""

	def validate(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Night cannot be before From Night."))
		if date_diff(self.to_date, self.from_date) + 1 > MAX_SEASON_NIGHTS:
			frappe.throw(_("A season can cover at most {0} nights.").format(MAX_SEASON_NIGHTS))

		plan = frappe.db.get_value("Rate Plan", self.rate_plan, ["property", "rate_basis"], as_dict=True)
		if plan.property != self.property:
			frappe.throw(_("Rate Plan {0} belongs to another property.").format(self.rate_plan))
		if plan.rate_basis != "Night":
			frappe.throw(
				_("Seasons generate nightly rates; Rate Plan {0} is priced per day use.").format(
					self.rate_plan
				)
			)

		seen = set()
		for row in self.rates:
			if row.room_type in seen:
				frappe.throw(_("Row {0}: Room Type {1} is listed twice.").format(row.idx, row.room_type))
			seen.add(row.room_type)
			if frappe.db.get_value("Room Type", row.room_type, "property") != self.property:
				frappe.throw(
					_("Row {0}: Room Type {1} belongs to another property.").format(row.idx, row.room_type)
				)
			if flt(row.weekday_rate) <= 0:
				frappe.throw(_("Row {0}: Weekday Rate must be more than 0.").format(row.idx))
			if flt(row.weekend_rate) < 0:
				frappe.throw(_("Row {0}: Weekend Rate cannot be negative.").format(row.idx))
