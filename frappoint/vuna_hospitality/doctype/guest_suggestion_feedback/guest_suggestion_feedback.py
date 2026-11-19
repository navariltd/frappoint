# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import suggestions


class GuestSuggestionFeedback(Document):
	"""A record of what staff did with a suggestion (plan F18). Written only by the service."""

	def validate(self):
		if not self.flags.get(suggestions.SERVICE_FLAG):
			frappe.throw(_("Suggestion feedback is recorded by the stay's page."), frappe.PermissionError)

	def on_trash(self):
		if not frappe.has_permission(self.doctype, "delete"):
			frappe.throw(_("Suggestion feedback is kept."))
