# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import inventory
from frappoint.vuna_hospitality.services.rooms import STATE_FIELDS, update_room_type_counts


class HotelRoom(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappoint.vuna_hospitality.doctype.hotel_room_feature_item.hotel_room_feature_item import (
			HotelRoomFeatureItem,
		)

		asset: DF.Link | None
		building: DF.Data | None
		capacity_override: DF.Int
		connecting_room: DF.Link | None
		features: DF.TableMultiSelect[HotelRoomFeatureItem]
		floor: DF.Int
		housekeeping_condition: DF.Literal["Inspected", "Clean", "Pickup", "Dirty"]
		housekeeping_zone: DF.Data | None
		is_active: DF.Check
		notes: DF.SmallText | None
		occupancy_status: DF.Literal["Vacant", "Reserved", "Due In", "Occupied", "Due Out", "Day Use"]
		property: DF.Link
		room_number: DF.Data
		room_type: DF.Link
		sellability: DF.Literal["Sellable", "Out of Service", "Out of Order"]
		service_unit: DF.Link | None
	# end: auto-generated types

	def autoname(self):
		# Room numbers are unique per property, so the record name carries both: e.g. "NBO1-201".
		self.room_number = (self.room_number or "").strip()
		self.name = f"{self.property}-{self.room_number}"

	def validate(self):
		self.room_number = (self.room_number or "").strip()
		self.validate_room_type()
		self.validate_connecting_room()
		self.validate_capacity_override()
		self.validate_state_fields_unchanged()

	def validate_room_type(self):
		room_type = frappe.db.get_value("Room Type", self.room_type, ["property", "is_active"], as_dict=True)
		if room_type.property != self.property:
			frappe.throw(
				_("Room Type {0} belongs to property {1}, not {2}.").format(
					self.room_type, room_type.property, self.property
				)
			)
		if not room_type.is_active and self.is_active:
			frappe.throw(_("Room Type {0} is inactive.").format(self.room_type))

	def validate_connecting_room(self):
		if not self.connecting_room:
			return
		if self.connecting_room == self.name:
			frappe.throw(_("A room cannot connect to itself."))
		other = frappe.db.get_value(
			"Hotel Room", self.connecting_room, ["property", "connecting_room"], as_dict=True
		)
		if other.property != self.property:
			frappe.throw(_("Connecting room {0} is in a different property.").format(self.connecting_room))
		if other.connecting_room and other.connecting_room != self.name:
			frappe.throw(
				_("Room {0} already connects to {1}.").format(self.connecting_room, other.connecting_room)
			)

	def validate_capacity_override(self):
		if self.capacity_override and self.capacity_override < 1:
			frappe.throw(_("Max Occupancy Override must be at least 1, or 0 to use the room type."))

	def validate_state_fields_unchanged(self):
		if self.is_new():
			return
		for fieldname in STATE_FIELDS:
			if self.has_value_changed(fieldname):
				frappe.throw(
					_("{0} changes through room actions, not by editing the room.").format(
						_(self.meta.get_label(fieldname))
					)
				)

	def on_update(self):
		self.sync_connecting_room()
		before = self.get_doc_before_save()
		update_room_type_counts(self.room_type, before.room_type if before else None)
		if not before or before.is_active != self.is_active or before.room_type != self.room_type:
			inventory.on_rooms_changed(self.property, self.room_type, before.room_type if before else None)

	def on_trash(self):
		if self.connecting_room:
			frappe.db.set_value("Hotel Room", self.connecting_room, "connecting_room", None)
		if frappe.db.exists("Room State Period", {"room": self.name, "docstatus": 1}):
			frappe.throw(_("Room {0} has submitted state periods. Cancel them first.").format(self.name))

	def after_delete(self):
		update_room_type_counts(self.room_type)
		inventory.on_rooms_changed(self.property, self.room_type)

	def sync_connecting_room(self):
		"""Keep the link two-way: setting A -> B also sets B -> A, and clears A's old partner."""
		before = self.get_doc_before_save()
		previous = before.connecting_room if before else None
		if previous and previous != self.connecting_room:
			frappe.db.set_value("Hotel Room", previous, "connecting_room", None)
		if self.connecting_room:
			frappe.db.set_value("Hotel Room", self.connecting_room, "connecting_room", self.name)

	def get_max_occupancy(self) -> int:
		return self.capacity_override or frappe.db.get_value("Room Type", self.room_type, "max_occupancy")
