# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, getdate

from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.rooms import OUT_OF_ORDER, refresh_room_sellability


class RoomStatePeriod(Document):
	"""A dated out-of-order or out-of-service period for one room.

	Submit to put it into effect; cancel to remove it. Nights are half-open: `from_date` is the
	first affected night and `to_date` the first night the room is usable again.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		affects_inventory: DF.Check
		amended_from: DF.Link | None
		assigned_to: DF.Link | None
		from_date: DF.Date
		naming_series: DF.Literal["RSP-.YYYY.-.#####"]
		nights: DF.Int
		property: DF.Link | None
		reason: DF.SmallText
		reported_by: DF.Link | None
		resolution_notes: DF.SmallText | None
		room: DF.Link
		room_type: DF.Link | None
		state: DF.Literal["Out of Order", "Out of Service"]
		to_date: DF.Date
	# end: auto-generated types

	def validate(self):
		room = frappe.db.get_value("Hotel Room", self.room, ["property", "room_type"], as_dict=True)
		self.property, self.room_type = room.property, room.room_type

		if getdate(self.to_date) <= getdate(self.from_date):
			frappe.throw(_("Back in Service On must be after From Date."))
		self.nights = date_diff(self.to_date, self.from_date)
		self.affects_inventory = 1 if self.state == OUT_OF_ORDER else 0
		self.validate_no_overlap()

	def validate_no_overlap(self):
		overlapping = frappe.get_all(
			"Room State Period",
			filters={
				"room": self.room,
				"docstatus": ["<", 2],
				"name": ["!=", self.name],
				"from_date": ["<", self.to_date],
				"to_date": [">", self.from_date],
			},
			fields=["name", "state", "from_date", "to_date"],
			limit=1,
		)
		if overlapping:
			other = overlapping[0]
			frappe.throw(
				_("Room {0} already has {1} {2} ({3} to {4}) overlapping these dates.").format(
					self.room,
					_(other.state),
					other.name,
					frappe.format(other.from_date, "Date"),
					frappe.format(other.to_date, "Date"),
				)
			)

	def on_submit(self):
		refresh_room_sellability(self.room)
		self.log("Room State Period Started")

	def on_cancel(self):
		refresh_room_sellability(self.room)
		self.log("Room State Period Cancelled")

	def log(self, event_type):
		log_event(
			"Hotel Room",
			self.room,
			event_type,
			to_status=self.state,
			reason=self.reason,
			property_name=self.property,
			data={
				"room_state_period": self.name,
				"from_date": str(self.from_date),
				"to_date": str(self.to_date),
				"affects_inventory": self.affects_inventory,
			},
		)
