# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from itertools import pairwise

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from frappoint.vuna_hospitality.services.pricing_masters import assert_fixed_revenue_code


class OccupancyPricingRule(Document):
	"""Extra-adult and child-band prices for a rate plan (design §10.4; plan F9)."""

	def validate(self):
		plan_property = frappe.db.get_value("Rate Plan", self.rate_plan, "property")
		if plan_property != self.property:
			frappe.throw(_("Rate Plan {0} belongs to another property.").format(self.rate_plan))
		if self.room_type and frappe.db.get_value("Room Type", self.room_type, "property") != self.property:
			frappe.throw(_("Room Type {0} belongs to another property.").format(self.room_type))
		if flt(self.extra_adult_amount) < 0:
			frappe.throw(_("The extra adult amount can't be negative."))
		if flt(self.extra_adult_amount):
			assert_fixed_revenue_code(self.extra_adult_charge_code, _("Extra Adult Charge Code"))
		self.validate_bands()
		self.validate_one_active_rule()

	def validate_bands(self):
		bands = sorted(self.child_bands, key=lambda band: band.from_age)
		for band in bands:
			if band.from_age < 0 or band.to_age > 17 or band.from_age > band.to_age:
				frappe.throw(
					_("Band {0}: ages must run from 0 to 17, from low to high.").format(band.band_name)
				)
			if band.price_as_adult:
				band.amount, band.charge_code = 0, None
			elif flt(band.amount) < 0:
				frappe.throw(_("Band {0}: the amount can't be negative.").format(band.band_name))
			elif flt(band.amount):
				assert_fixed_revenue_code(band.charge_code, _("Band {0}").format(band.band_name))
		for earlier, later in pairwise(bands):
			if later.from_age <= earlier.to_age:
				frappe.throw(_("Bands {0} and {1} overlap.").format(earlier.band_name, later.band_name))

	def validate_one_active_rule(self):
		if not self.is_active:
			return
		other = frappe.db.get_value(
			"Occupancy Pricing Rule",
			{
				"rate_plan": self.rate_plan,
				"room_type": self.room_type or ["is", "not set"],
				"is_active": 1,
				"name": ["!=", self.name or ""],
			},
			"name",
		)
		if other:
			frappe.throw(
				_("Rule {0} already prices {1} for this room type. Deactivate it first.").format(
					other, self.rate_plan
				)
			)
