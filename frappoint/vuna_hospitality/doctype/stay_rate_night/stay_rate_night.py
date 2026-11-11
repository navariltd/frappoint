# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import reservations


class StayRateNight(Document):
	"""The price of one night of a stay, as quoted when it was booked (design §30.12)."""

	def autoname(self):
		self.name = f"{self.stay_reservation}-{self.night_date}"

	def validate(self):
		reservations.guard_service_insert(self)


def on_doctype_update():
	frappe.db.add_unique(
		"Stay Rate Night", ["stay_reservation", "night_date"], constraint_name="unique_stay_night"
	)
