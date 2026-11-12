# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import night_audit
from frappoint.vuna_hospitality.services.status_commands import guard_status_change, register_transitions

# A failed run is queued again to restart its unfinished stages (plan F8).
register_transitions(
	"Night Audit Run",
	{
		"Queued": {"Running", "Failed"},
		"Running": {"Completed", "Failed"},
		"Failed": {"Queued"},
	},
	initial_statuses={"Queued"},
	reason_required={("*", "Failed")},
)


class NightAuditRun(Document):
	"""One night audit of one property's business date (design §21, §28.6; plan F8)."""

	def autoname(self):
		# One run per property and business date: the name is the guarantee.
		self.name = night_audit.run_name(self.property, self.business_date)

	def validate(self):
		if self.is_new() and not self.flags.get(night_audit.SERVICE_FLAG):
			frappe.throw(_("Night audit is started from the Night Audit page, not entered directly."))
		guard_status_change(self)

	def on_trash(self):
		if self.status in (night_audit.QUEUED, night_audit.RUNNING):
			frappe.throw(
				_("Night audit {0} is still {1} and can't be deleted.").format(self.name, _(self.status))
			)
