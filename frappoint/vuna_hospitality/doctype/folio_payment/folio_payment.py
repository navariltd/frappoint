# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import cashiering
from frappoint.vuna_hospitality.services.status_commands import (
	TRANSITION_FLAG,
	guard_status_change,
	register_transitions,
)

register_transitions(
	"Folio Payment",
	{"Pending": {"Received", "Failed", "Cancelled"}},
	initial_statuses={"Pending"},
	reason_required={("Pending", "Failed"), ("Pending", "Cancelled")},
)


class FolioPayment(Document):
	"""One payment (or refund) split across folios (design §16.2-16.3; plan F10)."""

	# The payments app's M-Pesa callback reads these two attributes from the document it calls.
	reference_name = None

	@property
	def grand_total(self):
		return self.amount

	def validate(self):
		if not (self.flags.get(cashiering.SERVICE_FLAG) or self.flags.get(TRANSITION_FLAG)):
			frappe.throw(_("Payments change only through the cashier actions."), frappe.PermissionError)
		guard_status_change(self)

	def on_payment_authorized(self, status: str | None = None):
		"""Called by the payment gateway when the guest has paid. Repeated calls change nothing."""
		if status in ("Authorized", "Completed"):
			cashiering.receive(self.name)

	def on_trash(self):
		if self.status == cashiering.RECEIVED:
			frappe.throw(_("A received payment can't be deleted. Refund it instead."), frappe.PermissionError)
