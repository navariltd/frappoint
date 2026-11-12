# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services.cashiering import SERVICE_FLAG
from frappoint.vuna_hospitality.services.status_commands import (
	TRANSITION_FLAG,
	guard_status_change,
	register_transitions,
)

register_transitions(
	"Cashier Shift",
	{"Open": {"Closed"}, "Closed": {"Reviewed"}},
	initial_statuses={"Open"},
)


class CashierShift(Document):
	"""A cashier's shift: float, payments taken, blind close, and review (design §16.1; plan F10)."""

	def validate(self):
		if not (self.flags.get(SERVICE_FLAG) or self.flags.get(TRANSITION_FLAG)):
			frappe.throw(_("Cashier shifts change only through the Cashier page."), frappe.PermissionError)
		guard_status_change(self)

	def on_trash(self):
		if frappe.db.exists("Folio Payment", {"cashier_shift": self.name}):
			frappe.throw(_("Shift {0} has payments and can't be deleted.").format(self.name))
