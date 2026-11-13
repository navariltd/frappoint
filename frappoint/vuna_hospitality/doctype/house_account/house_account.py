# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from frappoint.vuna_hospitality.services.status_commands import guard_status_change, register_transitions

register_transitions(
	"House Account",
	{"Active": {"Closed"}, "Closed": {"Active"}},
	initial_statuses={"Active"},
	reason_required={("Active", "Closed"), ("Closed", "Active")},
)


class HouseAccount(Document):
	"""A folio owner with no room (design §15.10; plan F12): staff meals, a conference."""

	def validate(self):
		guard_status_change(self)
		if self.account_type == "Event" and self.valid_from and self.valid_to:
			if getdate(self.valid_to) < getdate(self.valid_from):
				frappe.throw(_("The account can't end before it starts."))
		if (
			not self.is_new()
			and self.has_value_changed("current_folio")
			and not self.flags.get("from_house_account_service")
		):
			frappe.throw(_("The current folio is set by the house account's postings."))
		if self.payee_customer and not self.is_new() and self.has_value_changed("payee_customer"):
			from frappoint.vuna_hospitality.services.house_accounts import check_payee_change

			check_payee_change(self)

	def on_trash(self):
		if frappe.db.exists("Guest Folio", {"house_account": self.name}):
			frappe.throw(_("House Account {0} has folios. Close it instead.").format(self.name))
