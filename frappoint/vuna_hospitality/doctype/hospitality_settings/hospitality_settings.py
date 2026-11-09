# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class HospitalitySettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accent_color: DF.Color
		body_text_color: DF.Color
		company: DF.Link
		enable_hospitality: DF.Check
		favicon: DF.Attach | None
		light_surface_color: DF.Color
		logo: DF.Attach | None
		page_background_color: DF.Color
		page_title: DF.Data
		primary_color: DF.Color
		primary_hover_color: DF.Color
		use_24_clock_system: DF.Check
	# end: auto-generated types

	pass
