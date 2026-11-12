# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services.allowances import SERVICE_FLAG


class PackageAllowanceEntry(Document):
	"""One movement of a package allowance: granted, consumed, or expired. Never changed."""

	def validate(self):
		if not self.is_new() or not self.flags.get(SERVICE_FLAG):
			frappe.throw(
				_("Allowance entries are written by folio postings and night audit."), frappe.PermissionError
			)

	def on_trash(self):
		frappe.throw(_("Allowance entries can't be deleted."), frappe.PermissionError)
