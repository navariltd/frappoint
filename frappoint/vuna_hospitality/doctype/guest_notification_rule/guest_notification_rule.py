# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import notifications


class GuestNotificationRule(Document):
	"""When to message guests, how, and what to say (plan F20)."""

	def validate(self):
		if self.event in notifications.TIMED_EVENTS and (self.offset or 0) < 0:
			frappe.throw(_("The offset can't be negative."))
		if self.channel == "Email" and not self.email_template:
			frappe.throw(_("Pick the Email Template to send."))
		if self.channel == "SMS" and not (self.sms_message or "").strip():
			frappe.throw(_("Write the SMS message."))
