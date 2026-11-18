# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import maintenance


class MaintenanceRequest(Document):
	"""A fault in a room or its equipment (plan F17). Changed only by the maintenance service."""

	def validate(self):
		if not self.flags.get(maintenance.SERVICE_FLAG):
			frappe.throw(
				_("Maintenance requests change only from the Housekeeping Board."), frappe.PermissionError
			)

	def on_trash(self):
		frappe.throw(_("Maintenance requests are kept for the room's history. Cancel the request instead."))
