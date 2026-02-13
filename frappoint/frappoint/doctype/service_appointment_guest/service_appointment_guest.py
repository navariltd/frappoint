# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ServiceAppointmentGuest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		email: DF.Data | None
		full_name: DF.Data
		is_primary: DF.Check
		mobile_no: DF.Data | None
		notes: DF.TextEditor | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types
	pass
