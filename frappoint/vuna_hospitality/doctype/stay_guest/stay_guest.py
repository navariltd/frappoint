# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from frappoint.vuna_hospitality.services import reservations
from frappoint.vuna_hospitality.services.status_commands import guard_status_change, register_transitions

register_transitions(
	"Stay Guest",
	{
		"Expected": {"Registered", "Checked In", "Did Not Stay", "Removed"},
		"Registered": {"Checked In", "Did Not Stay", "Removed"},
		"Checked In": {"Checked Out"},
	},
	initial_statuses={"Expected"},
	reason_required={("*", "Removed")},
)


class StayGuest(Document):
	"""One person's part in a stay: role, age category, registration and check-in (design §30.13)."""

	def validate(self):
		reservations.guard_service_insert(self)
		guard_status_change(self)
