# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import folio as folio_service
from frappoint.vuna_hospitality.services.status_commands import (
	TRANSITION_FLAG,
	guard_status_change,
	register_transitions,
)

# Design §8.1 and §15.9. F7 opens folios and closes idle ones; settlement and AR (F11) and
# post-stay folios (F12) use the rest.
register_transitions(
	"Guest Folio",
	{
		"Open": {"Settlement Pending", "Settled", "Transferred to AR", "Post-Stay Open", "Closed"},
		"Settlement Pending": {"Open", "Settled", "Transferred to AR"},
		"Post-Stay Open": {"Settlement Pending", "Settled", "Transferred to AR", "Closed"},
		"Settled": {"Closed"},
		"Closed": {"Open"},
	},
	initial_statuses={"Open"},
	reason_required={("Closed", "Open")},
)

# Staff may rename a folio window and keep notes on it. Everything else is set by the service.
EDITABLE_FIELDS = {"folio_label", "notes"}


class GuestFolio(Document):
	"""The running tab of one payee (design §15, §30.16). Its lines are Folio Transactions."""

	def validate(self):
		if self.is_new():
			if not self.flags.get(folio_service.SERVICE_FLAG):
				frappe.throw(_("Folios are opened from the stay, not entered directly."))
		else:
			self.guard_service_fields()
		guard_status_change(self)

	def guard_service_fields(self):
		if self.flags.get(folio_service.SERVICE_FLAG) or self.flags.get(TRANSITION_FLAG):
			return
		changed = [
			df.fieldname
			for df in self.meta.fields
			if df.fieldname not in EDITABLE_FIELDS
			and df.fieldtype not in ("Section Break", "Column Break", "Tab Break")
			and df.fieldname != "status"
			and self.has_value_changed(df.fieldname)
		]
		if changed:
			frappe.throw(
				_("These folio fields change only through folio actions: {0}.").format(
					", ".join(_(self.meta.get_label(fieldname)) for fieldname in changed)
				)
			)

	def on_trash(self):
		if frappe.db.exists(folio_service.TRANSACTION, {"guest_folio": self.name}):
			frappe.throw(_("Folio {0} has transactions and can't be deleted.").format(self.name))
		if self.stay_reservation:
			frappe.db.set_value(
				"Stay Reservation",
				{"name": self.stay_reservation, "default_folio": self.name},
				"default_folio",
				None,
				update_modified=False,
			)
