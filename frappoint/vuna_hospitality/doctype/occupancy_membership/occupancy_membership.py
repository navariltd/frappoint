# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from frappoint.vuna_hospitality.services import reservations


class OccupancyMembership(Document):
	"""Links a stay to the room occupancy it uses, for a date range (design §30.10)."""

	def validate(self):
		reservations.guard_service_insert(self)
