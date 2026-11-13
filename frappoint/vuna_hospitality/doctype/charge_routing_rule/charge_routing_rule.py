# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import routing


class ChargeRoutingRule(Document):
	"""Sends a stay's automatic charges to one of its folios (design §15.6, tier 3; plan F12)."""

	def validate(self):
		if not self.flags.get(routing.SERVICE_FLAG):
			frappe.throw(_("Routing rules change only from the Folio Workspace."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Routing rules are kept for the stay's history. Remove the rule instead."))
