# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import guest_dedup


class GuestProfileMerge(Document):
	"""The audit record of one profile merge (plan F14). Written only by the service."""

	def validate(self):
		if not self.flags.get(guest_dedup.SERVICE_FLAG):
			frappe.throw(_("Profiles are merged from the Guest History page."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Merge records are kept for the audit trail. Unmerge instead."))
