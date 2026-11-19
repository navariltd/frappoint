# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import guest_history


class GuestHistoryMatch(Document):
	"""A legacy appointment guest proposed as a Guest Profile (plan F18). Reviewed on the desk."""

	def validate(self):
		if not self.flags.get(guest_history.SERVICE_FLAG):
			frappe.throw(
				_("Guest history matches are reviewed from the Guest History page."), frappe.PermissionError
			)
