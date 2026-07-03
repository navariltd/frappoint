# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, get_link_to_form, getdate, today


class ServiceType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappoint.frappoint.doctype.service_type_material.service_type_material import (
			ServiceTypeMaterial,
		)
		from frappoint.frappoint.doctype.service_type_payment_gateway.service_type_payment_gateway import (
			ServiceTypePaymentGateway,
		)
		from frappoint.frappoint.doctype.service_type_price.service_type_price import ServiceTypePrice
		from frappoint.frappoint.doctype.service_type_unit_type.service_type_unit_type import (
			ServiceTypeUnitType,
		)

		appointment_type: DF.Data
		benefits: DF.TextEditor | None
		buffer_after: DF.Int
		buffer_before: DF.Int
		company: DF.Link
		confirmation_deposit_percent: DF.Percent
		consumables: DF.Table[ServiceTypeMaterial]
		default_duration_in_minutes: DF.Int
		description: DF.TextEditor | None
		disabled: DF.Check
		image: DF.AttachImage | None
		item: DF.Link
		item_group: DF.Data | None
		item_name: DF.Data | None
		max_clients_per_slot: DF.Int
		max_guests: DF.Int
		min_guests: DF.Int
		payment_gateways: DF.Table[ServiceTypePaymentGateway]
		prices: DF.Table[ServiceTypePrice]
		service_unit_types: DF.Table[ServiceTypeUnitType]
		short_description: DF.Data | None
		tags: DF.SmallText | None
		techniques: DF.TextEditor | None
	# end: auto-generated types
	pass

	def validate(self):
		self.validate_default_duration()
		self.validate_max_clients()
		self.validate_confirmation_deposit_percent()
		self.validate_item_link()
		self.validate_service_unit_types()
		self.validate_prices()
		self.validate_consumables()
		self.auto_create_item_if_missing()

	def on_update(self):
		self.invalidate_slot_cache()

	def invalidate_slot_cache(self):
		from ...services.slot_cache_service import invalidate_service_date_range_cache

		start = getdate(today())
		horizon = int(frappe.db.get_single_value("Service Appointment Settings", "max_advance_days") or 30)
		end = add_days(start, max(0, horizon))
		invalidate_service_date_range_cache(self.name, start, end)

	def validate_default_duration(self):
		if self.default_duration_in_minutes <= 0:
			frappe.throw("Default duration must be greater than zero.")
		if self.default_duration_in_minutes > 1440:
			frappe.throw("Duration cannot exceed 24 hours")

	def validate_max_clients(self):
		if self.max_clients_per_slot < 1:
			frappe.throw("Clients per slot must be at least 1")

	def validate_confirmation_deposit_percent(self):
		if self.confirmation_deposit_percent is None:
			return

		if self.confirmation_deposit_percent < 0 or self.confirmation_deposit_percent > 100:
			frappe.throw(_("Confirmation Deposit (%) must be between 0 and 100"))

	def validate_item_link(self):
		if self.item:
			if frappe.db.get_value("Item", self.item, "is_stock_item"):
				frappe.throw(_("Item {0} must be a non-stock/service item").format(self.item))

	def validate_service_unit_types(self):
		self._validate_no_duplicates(
			items=self.service_unit_types,
			fields_to_check=["service_unit_type"],
			error_title="Duplicate Service Unit Types",
			item_label="service unit type",
		)

	def validate_prices(self):
		if not self.prices:
			frappe.throw(_("At least one valid Price is required."), title=_("Missing Price."))
		self._validate_no_duplicates(
			items=self.prices,
			fields_to_check=["price_name", "duration"],
			error_title="Duplicate Prices",
			item_label="price list",
		)

		# Validate price values
		self._validate_positive_prices()

	def _validate_positive_prices(self):
		invalid_prices = [
			{"row": idx, "price_name": price.price_name, "amount": price.amount or 0}
			for idx, price in enumerate(self.prices, start=1)
			if price.amount is not None and price.amount <= 0
		]

		if invalid_prices:
			error_messages = [
				f"Row {item['row']}: <b>{item['price_name']}</b> - Amount must be greater than 0 (currently {item['amount']})"
				for item in invalid_prices
			]

			frappe.throw(
				"Invalid price rates found:<br>" + "<br>".join(error_messages), title="Invalid Prices"
			)

	def _validate_no_duplicates(self, items, fields_to_check, error_title, item_label):
		"""
		Generic function to validate no duplicates in child table

		Args:
			items: Child table items to validate
			fields_to_check: List of field names to form a unique key (e.g. ["price_name", "duration"])
			error_title: Title for the error message
			item_label: Human-readable label for the item (singular)
		"""
		item_rows = {}

		for idx, item in enumerate(items, start=1):
			key_values = tuple(getattr(item, f, None) for f in fields_to_check)
			if all(key_values):  # only check if all relevant fields are filled
				if key_values not in item_rows:
					item_rows[key_values] = []
				item_rows[key_values].append(idx)

		duplicates = {value: rows for value, rows in item_rows.items() if len(rows) > 1}

		if duplicates:
			error_messages = []
			for value, rows in sorted(duplicates.items()):
				key_str = ", ".join(f"<b>{f}</b>: {v}" for f, v in zip(fields_to_check, value, strict=True))
				row_list = ", ".join(map(str, rows))
				error_messages.append(f"{key_str} → rows: {row_list}")

			plural_label = f"{item_label}s" if not item_label.endswith("s") else item_label
			frappe.throw(
				f"Duplicate {plural_label} found:<br>" + "<br>".join(error_messages), title=error_title
			)

	def validate_consumables(self):
		if not self.consumables:
			return

		for item in self.consumables:
			is_stock_item = frappe.db.get_value("Item", item.item, "is_stock_item")
			if not is_stock_item:
				frappe.throw(_("Consumable item {0} must be a stock item").format(item.item_code))

	@frappe.whitelist()
	def get_appointment_settings(self):
		return frappe.get_single("Service Appointment Settings")

	def auto_create_item_if_missing(self):
		settings = self.get_appointment_settings()

		if not settings.auto_create_service_items:
			return

		if self.item and frappe.db.exists("Item", self.item):
			return

		item_name = self.service_type

		item_doc = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_name,
				"item_name": item_name,
				"item_group": settings.default_item_group,
				"is_stock_item": 0,
				"is_sales_item": 1,
			}
		)
		item_doc.insert(ignore_permissions=True)

		item_doc_link = get_link_to_form("Item", item_doc.name)
		frappe.msgprint(
			_("Service Item <b>{0}</b> created.").format(item_doc_link), indicator="green", alert=True
		)

	def get_required_materials(self):
		materials = []
		for item in self.consumables:
			materials.append(
				{"item_code": item.item, "qty": item.qty, "uom": item.uom, "warehouse": item.s_warehouse}
			)

		return materials
