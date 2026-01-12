# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ServiceUnitType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_appointments: DF.Check
		allow_overlap: DF.Check
		company: DF.Link
		disabled: DF.Check
		is_billable: DF.Check
		item_code: DF.Link | None
		rate__uom: DF.Float
		uom: DF.Link | None
	# end: auto-generated types
	pass
