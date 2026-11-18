# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import preferences


class GuestPreference(Document):
	"""A preference the guest declared or staff confirmed (plan F18). Ranking reads it."""

	def validate(self):
		self.value = (self.value or "").strip()
		if self.reference_doctype and self.reference_doctype not in preferences.REFERENCE_DOCTYPES:
			frappe.throw(
				_("A preference refers to a {0}, not a {1}.").format(
					", ".join(_(name) for name in preferences.REFERENCE_DOCTYPES), _(self.reference_doctype)
				)
			)
		preferences.validate_matchable(self)
