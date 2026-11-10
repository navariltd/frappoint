# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from frappoint.vuna_hospitality.services.rates import SERVICE_FLAG, rate_day_name

UNIQUE_INDEX = "unique_rate_plan_room_type_night"


class RoomRateDay(Document):
	"""The price of one room type on one rate plan for one night: the single source of truth."""

	def autoname(self):
		code = frappe.db.get_value("Room Type", self.room_type, "code")
		self.name = rate_day_name(self.rate_plan, code, self.rate_date)

	def validate(self):
		plan_property = frappe.db.get_value("Rate Plan", self.rate_plan, "property")
		if frappe.db.get_value("Room Type", self.room_type, "property") != plan_property:
			frappe.throw(
				_("Room Type {0} and Rate Plan {1} belong to different properties.").format(
					self.room_type, self.rate_plan
				)
			)
		self.property = plan_property
		if flt(self.rate) < 0:
			frappe.throw(_("Rate cannot be negative."))

		# Anything not written by the rate service is a hand edit, which season generation preserves.
		if not self.flags.get(SERVICE_FLAG) and (self.is_new() or self.has_value_changed("rate")):
			self.source = "Manual"
			self.is_manual_override = 1


def on_doctype_update():
	frappe.db.add_unique(
		"Room Rate Day", ["rate_plan", "room_type", "rate_date"], constraint_name=UNIQUE_INDEX
	)
