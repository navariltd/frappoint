# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import housekeeping


class HousekeepingTask(Document):
	"""One piece of room work and its inspection (plan F17). Changed only by the housekeeping service."""

	def validate(self):
		if not self.flags.get(housekeeping.SERVICE_FLAG):
			frappe.throw(
				_("Housekeeping tasks change only from the Housekeeping Board."), frappe.PermissionError
			)

	def on_trash(self):
		frappe.throw(_("Housekeeping tasks are kept for the room's history. Cancel the task instead."))
