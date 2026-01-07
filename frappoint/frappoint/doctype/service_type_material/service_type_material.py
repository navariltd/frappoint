# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ServiceTypeMaterial(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		conversion_factor: DF.Float
		cost_center: DF.Link | None
		description: DF.SmallText | None
		item: DF.Link
		item_name: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		qty: DF.Float
		s_warehouse: DF.Link | None
		stock_uom: DF.Link | None
		uom: DF.Link
		valuation_rate: DF.Float
	# end: auto-generated types
	pass
