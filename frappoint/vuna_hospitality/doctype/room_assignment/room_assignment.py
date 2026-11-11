# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from frappoint.vuna_hospitality.services import reservations
from frappoint.vuna_hospitality.services.status_commands import guard_status_change, register_transitions

register_transitions(
	"Room Assignment",
	{"Assigned": {"Occupied", "Cancelled"}, "Occupied": {"Released"}},
	initial_statuses={"Assigned", "Occupied"},
)


class RoomAssignment(Document):
	"""A dated segment of a stay in one physical room (design §30.14). A move ends one and starts the next."""

	def validate(self):
		reservations.guard_service_insert(self)
		guard_status_change(self)
