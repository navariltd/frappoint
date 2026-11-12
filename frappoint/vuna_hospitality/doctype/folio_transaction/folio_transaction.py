# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import folio as folio_service


class FolioTransaction(Document):
	"""One immutable folio line (design §15.4, §28.3, §30.17).

	The posting service creates and submits it in one step. After that it can't be edited,
	cancelled, amended, or deleted, by anyone: a wrong line is corrected with a reversal.
	"""

	def validate(self):
		if not self.is_new() or not self.flags.get(folio_service.SERVICE_FLAG):
			frappe.throw(
				_("Folio transactions are posted by the folio service and can't be entered or edited."),
				frappe.PermissionError,
			)

	def on_update_after_submit(self):
		frappe.throw(_("Folio transactions can't be changed. Reverse it instead."), frappe.PermissionError)

	def before_cancel(self):
		frappe.throw(_("Folio transactions can't be cancelled. Reverse it instead."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Folio transactions can't be deleted. Reverse it instead."), frappe.PermissionError)


def on_doctype_update():
	frappe.db.add_index("Folio Transaction", ["guest_folio", "docstatus"])
