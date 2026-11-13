# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import deposits
from frappoint.vuna_hospitality.services.status_commands import (
	TRANSITION_FLAG,
	guard_status_change,
	register_transitions,
)

# Design §16.4. Requested, Partly Paid and Received follow the payments; the rest are commands.
_OPEN = {"Requested", "Partly Paid", "Received"}
register_transitions(
	"Guest Deposit",
	{
		**{
			status: (_OPEN - {status}) | {"Applied", "Forfeited", "Refunded", "Waived", "Released"}
			for status in _OPEN
		},
		"Released": {"Requested", "Partly Paid", "Received"},
		"Waived": {"Requested", "Partly Paid", "Received"},
	},
	initial_statuses={"Requested"},
	reason_required={("*", "Waived"), ("*", "Released")},
)


class GuestDeposit(Document):
	"""The link from a stay to the Payment Entries that paid its deposit (design §16.4; plan F12).

	Amounts paid and refunded are read from those Payment Entries, never stored here twice.
	"""

	def validate(self):
		if not (self.flags.get(deposits.SERVICE_FLAG) or self.flags.get(TRANSITION_FLAG)):
			frappe.throw(_("Deposits change only through the deposit actions."), frappe.PermissionError)
		guard_status_change(self)

	def on_trash(self):
		if frappe.db.exists("Folio Payment", {"guest_deposit": self.name}):
			frappe.throw(_("Deposit {0} has payments and can't be deleted.").format(self.name))
