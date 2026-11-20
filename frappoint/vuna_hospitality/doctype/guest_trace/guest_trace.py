# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import guest_messages


class GuestTrace(Document):
	"""A dated departmental follow-up for a stay (plan F20). Changed only by the guest messages service."""

	def validate(self):
		if not self.flags.get(guest_messages.SERVICE_FLAG):
			frappe.throw(_("Traces are set and resolved from the stay's page."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Traces are kept with the stay. Cancel the trace instead."))
