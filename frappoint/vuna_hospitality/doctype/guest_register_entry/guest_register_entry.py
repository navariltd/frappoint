# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import guest_register


class GuestRegisterEntry(Document):
	"""One guest's statutory register snapshot, taken at check-in (plan F20)."""

	def validate(self):
		if not self.flags.get(guest_register.SERVICE_FLAG):
			frappe.throw(_("The guest register is written at check-in."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("The guest register is a statutory record and is kept for the statutory period."))
