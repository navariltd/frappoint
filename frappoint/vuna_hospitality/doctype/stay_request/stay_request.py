# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import preferences


class StayRequest(Document):
	"""A request for one stay (plan F18). Changed only by the preferences service."""

	def validate(self):
		if not self.flags.get(preferences.SERVICE_FLAG):
			frappe.throw(_("Stay requests change only from the stay's page."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Stay requests are kept with the stay. Cancel the request instead."))
