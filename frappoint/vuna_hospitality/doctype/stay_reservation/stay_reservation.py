# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import reservations
from frappoint.vuna_hospitality.services.status_commands import guard_status_change, register_transitions

# Plan F5 lifecycle. F5 runs hold, confirm, cancel and expiry; night audit (F8), check-in and
# check-out (F6) and reinstatement (F12) use the rest.
register_transitions(
	"Stay Reservation",
	{
		"Held": {"Confirmed", "Expired", "Cancelled"},
		# Confirmed -> In House: check-in on the arrival business date before night audit (F8) marks
		# the stay Due In.
		"Confirmed": {"Due In", "In House", "Cancelled"},
		"Due In": {"In House", "No Show", "Cancelled"},
		"In House": {"Due Out", "Checked Out"},
		"Due Out": {"In House", "Checked Out"},
		"Cancelled": {"Confirmed"},
		"No Show": {"Confirmed", "In House"},
	},
	initial_statuses={"Held"},
	reason_required={("*", "Cancelled")},
)


class StayReservation(Document):
	"""One guest stay: dates, room type, rate plan, status and policy snapshot (design §30.11)."""

	def validate(self):
		reservations.guard_service_insert(self)
		guard_status_change(self)
		if not self.is_new():
			reservations.guard_locked_fields(
				self,
				(
					"arrival_date",
					"departure_date",
					"room_type",
					"rate_plan",
					"hotel_booking",
					"lead_guest",
					"property",
				),
			)

	def on_trash(self):
		if self.status not in reservations.INACTIVE_STAY_STATUSES:
			frappe.throw(_("Cancel stay {0} before deleting it.").format(self.name))
		frappe.db.delete("Stay Rate Night", {"stay_reservation": self.name})
		frappe.db.delete("Occupancy Membership", {"stay_reservation": self.name})
