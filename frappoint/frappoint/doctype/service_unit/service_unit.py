# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ServiceUnit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		active: DF.Check
		allow_appointments: DF.Check
		allow_overlap: DF.Check
		capacity: DF.Int
		company: DF.Link
		is_group: DF.Check
		lft: DF.Int
		location: DF.Link | None
		old_parent: DF.Link | None
		parent_service_unit: DF.Link | None
		rgt: DF.Int
		unit_name: DF.Data
		unit_type: DF.Link
	# end: auto-generated types
	pass
