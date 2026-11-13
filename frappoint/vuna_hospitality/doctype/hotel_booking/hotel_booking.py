# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import reservations
from frappoint.vuna_hospitality.services.status_commands import guard_status_change, register_transitions

_STATUSES = {"Option", "Confirmed", "Partly Cancelled", "Cancelled"}

# The booking status follows its stays (see reservations.refresh_booking): any move between these
# is allowed, but only the reservation service makes it. Closed comes with check-out (F6) and
# no-shows; reinstating a no-show (F12) opens the booking again.
register_transitions(
	"Hotel Booking",
	{
		**{status: (_STATUSES | {"Closed"}) - {status} for status in _STATUSES},
		"Closed": set(_STATUSES) - {"Option"},
	},
	initial_statuses={"Option"},
)


class HotelBooking(Document):
	"""The commercial booking: who booked, through which source, and its stays (design §30.8)."""

	def validate(self):
		reservations.guard_service_insert(self)
		guard_status_change(self)

	def on_trash(self):
		active = frappe.get_all(
			"Stay Reservation",
			filters={"hotel_booking": self.name, "status": ["not in", reservations.INACTIVE_STAY_STATUSES]},
			pluck="name",
		)
		if active:
			frappe.throw(_("Cancel the booking's stays before deleting it: {0}.").format(", ".join(active)))
		for stay in frappe.get_all("Stay Reservation", filters={"hotel_booking": self.name}, pluck="name"):
			frappe.delete_doc("Stay Reservation", stay, ignore_permissions=True)
		for occupancy in frappe.get_all("Room Occupancy", filters={"hotel_booking": self.name}, pluck="name"):
			frappe.delete_doc("Room Occupancy", occupancy, ignore_permissions=True)
