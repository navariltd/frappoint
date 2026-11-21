# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import guest_messages


class GuestMessage(Document):
	"""A message for an in-house guest (plan F20). Changed only by the guest messages service."""

	def validate(self):
		if not self.flags.get(guest_messages.SERVICE_FLAG):
			frappe.throw(
				_("Guest messages are taken and delivered from the stay's page."), frappe.PermissionError
			)

	def on_trash(self):
		frappe.throw(_("Guest messages are kept with the stay."))
