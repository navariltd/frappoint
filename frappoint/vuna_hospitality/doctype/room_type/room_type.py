# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services.rooms import normalize_code


class RoomType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappoint.vuna_hospitality.doctype.room_type_amenity.room_type_amenity import RoomTypeAmenity

		allows_cot: DF.Check
		allows_extra_bed: DF.Check
		amenities: DF.TableMultiSelect[RoomTypeAmenity]
		base_adults: DF.Int
		bed_configuration: DF.SmallText | None
		code: DF.Data
		day_use_capacity: DF.Int
		description: DF.TextEditor | None
		is_active: DF.Check
		max_adults: DF.Int
		max_children: DF.Int
		max_occupancy: DF.Int
		overbooking_limit: DF.Int
		property: DF.Link
		room_count: DF.Int
		room_type_name: DF.Data
		sort_order: DF.Int
	# end: auto-generated types

	def autoname(self):
		# Codes are unique per property, so the record name carries both: e.g. "NBO1-DLX".
		self.code = normalize_code(self.code, "Code")
		self.name = f"{self.property}-{self.code}"

	def before_validate(self):
		self.code = normalize_code(self.code, "Code")

	def validate(self):
		self.validate_capacity()

	def validate_capacity(self):
		if self.max_occupancy < 1:
			frappe.throw(_("Max Occupancy must be at least 1."))
		if self.max_adults < 1:
			frappe.throw(_("Max Adults must be at least 1."))
		if self.base_adults > self.max_adults:
			frappe.throw(_("Base Adults cannot be more than Max Adults."))
		if self.max_adults > self.max_occupancy:
			frappe.throw(_("Max Adults cannot be more than Max Occupancy."))
		if self.max_children > self.max_occupancy:
			frappe.throw(_("Max Children cannot be more than Max Occupancy."))

	def on_trash(self):
		if frappe.db.exists("Hotel Room", {"room_type": self.name}):
			frappe.throw(_("Room Type {0} still has rooms. Move or delete them first.").format(self.name))
