# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BookingDeskSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accent_color: DF.Color | None
		body_text_color: DF.Color | None
		company: DF.Link | None
		favicon: DF.AttachImage | None
		light_surface_color: DF.Color | None
		page_background_color: DF.Color | None
		page_title: DF.Data | None
		primary_color: DF.Color | None
		primary_hover_color: DF.Color | None
		sidebar_logo: DF.AttachImage | None
	# end: auto-generated types

	pass
