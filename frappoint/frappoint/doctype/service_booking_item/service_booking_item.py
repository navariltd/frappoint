# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ServiceBookingItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cancelled_qty: DF.Int
		currency: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		pricing_model: DF.Literal["", "Per Booking", "Per Guest", "Guest Tier"]
		qty: DF.Int
		rate: DF.Currency
		service_type: DF.Link | None
		total_amount: DF.Currency
	# end: auto-generated types
	pass
