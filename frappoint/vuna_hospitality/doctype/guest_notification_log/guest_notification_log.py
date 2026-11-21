# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import notifications


class GuestNotificationLog(Document):
	"""A guest message sent by a rule, kept so it is sent once (plan F20)."""

	def validate(self):
		if not self.flags.get(notifications.SERVICE_FLAG):
			frappe.throw(
				_("Notification logs are written by the notification service."), frappe.PermissionError
			)

	def on_trash(self):
		frappe.throw(_("Notification logs are kept as the record of what guests were sent."))
