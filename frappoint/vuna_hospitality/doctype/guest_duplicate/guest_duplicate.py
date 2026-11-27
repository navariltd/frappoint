# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import guest_dedup


class GuestDuplicate(Document):
	"""Two profiles that may be one person, for review (plan F14). Written only by the service."""

	def validate(self):
		if not self.flags.get(guest_dedup.SERVICE_FLAG):
			frappe.throw(
				_("Duplicate profiles are reviewed from the Guest History page."), frappe.PermissionError
			)

	def on_trash(self):
		frappe.throw(_("Duplicate reviews are kept as the record of what was decided."))
