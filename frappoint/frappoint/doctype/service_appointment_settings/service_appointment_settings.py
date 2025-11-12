# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ServiceAppointmentSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auto_create_service_items: DF.Check
		default_item_group: DF.Link | None
		lead_time_hours: DF.Int
		max_advance_days: DF.Int
		use_erpnext_pricing: DF.Check
	# end: auto-generated types
	pass
