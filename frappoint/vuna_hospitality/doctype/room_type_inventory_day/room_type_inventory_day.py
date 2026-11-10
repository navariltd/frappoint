# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

UNIQUE_INDEX = "unique_property_room_type_night"


class RoomTypeInventoryDay(Document):
	"""Per-night counters for one room type (design §9.3, §28.4).

	Rows are created and changed only by `services.inventory`, which locks them with
	SELECT ... FOR UPDATE. They are a cache: `rebuild()` recomputes them from the real records.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		available: DF.Int
		block_unpicked: DF.Int
		day_use_capacity: DF.Int
		day_use_sold: DF.Int
		held: DF.Int
		inventory_date: DF.Date
		last_rebuilt_at: DF.Datetime | None
		out_of_order: DF.Int
		out_of_service: DF.Int
		overbooking_limit: DF.Int
		physical_rooms: DF.Int
		property: DF.Link
		room_type: DF.Link
		sold: DF.Int
	# end: auto-generated types

	def autoname(self):
		# One row per room type and night; the room type name already carries the property.
		self.name = f"{self.room_type}-{self.inventory_date}"

	def validate(self):
		if not self.flags.get("from_inventory_service"):
			frappe.throw(_("Room Type Inventory Day rows are maintained by the inventory service only."))


def on_doctype_update():
	frappe.db.add_unique(
		"Room Type Inventory Day", ["property", "room_type", "inventory_date"], constraint_name=UNIQUE_INDEX
	)
