# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import reservations
from frappoint.vuna_hospitality.services.status_commands import guard_status_change, register_transitions

register_transitions(
	"Room Occupancy",
	{"Held": {"Confirmed", "Released", "Cancelled"}, "Confirmed": {"Cancelled", "Released"}},
	status_field="allocation_state",
	initial_statuses={"Held"},
)


class RoomOccupancy(Document):
	"""The physical-room demand a stay puts on inventory, counted once (design §30.9)."""

	def validate(self):
		reservations.guard_service_insert(self)
		guard_status_change(self)

	def on_trash(self):
		if self.allocation_state in reservations.ACTIVE_ALLOCATIONS:
			frappe.throw(
				_("Room Occupancy {0} still holds inventory. Cancel its stay first.").format(self.name)
			)
		frappe.db.delete("Occupancy Membership", {"room_occupancy": self.name})
