# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form, getdate, today


class AppointmentType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from frappoint.frappoint.doctype.appointment_type_material.appointment_type_material import AppointmentTypeMaterial
		from frappoint.frappoint.doctype.appointment_type_price.appointment_type_price import AppointmentTypePrice
		from frappoint.frappoint.doctype.appointment_type_provider.appointment_type_provider import AppointmentTypeProvider
		from frappoint.frappoint.doctype.appointment_type_service_unit.appointment_type_service_unit import AppointmentTypeServiceUnit

		appointment_type: DF.Data
		buffer_after: DF.Int
		buffer_before: DF.Int
		company: DF.Link
		consumables: DF.Table[AppointmentTypeMaterial]
		default_duration_in_minutes: DF.Int
		description: DF.SmallText | None
		disabled: DF.Check
		item: DF.Link
		item_group: DF.Data | None
		item_name: DF.Data | None
		max_clients_per_slot: DF.Int
		prices: DF.Table[AppointmentTypePrice]
		providers: DF.Table[AppointmentTypeProvider]
		service_units: DF.Table[AppointmentTypeServiceUnit]
	# end: auto-generated types
	pass

	def validate(self):
		self.validate_default_duration()
		self.validate_max_clients()
		self.validate_item_link()
		self.validate_providers()
		self.validate_service_units()
		self.validate_prices()
		self.validate_consumables()
		self.auto_create_item_if_missing()

	def on_update(self):
		self.sync_item_prices()

	def validate_default_duration(self):
		if self.default_duration_in_minutes <= 0:
			frappe.throw("Default duration must be greater than zero.")
		if self.default_duration_in_minutes > 1440:
			frappe.throw("Duration cannot exceed 24 hours")

	def validate_max_clients(self):
		if self.max_clients_per_slot < 1:
			frappe.throw("Clients per slot must be at least 1")

	def validate_item_link(self):
		if self.item:
			if frappe.db.get_value("Item", self.item, "is_stock_item"):
				frappe.throw(_("Item {0} must be a non-stock/service item").format(self.item))

	def validate_providers(self):
		valid_providers = [p for p in self.providers if p.provider]
		if not valid_providers:
			frappe.throw("At least one valid <b>Provider</b> is required.", title="Missing Provider")

		self._validate_no_duplicates(
			items=self.providers,
			fields_to_check=["provider"],
			error_title="Duplicate Providers",
			item_label="provider",
		)

	def validate_service_units(self):
		self._validate_no_duplicates(
			items=self.service_units,
			fields_to_check=["service_unit"],
			error_title="Duplicate Service Units",
			item_label="service unit",
		)

	def validate_prices(self):
		self._validate_no_duplicates(
			items=self.prices,
			fields_to_check=["price_list", "uom"],
			error_title="Duplicate Price Lists",
			item_label="price list",
		)

		# Validate price values
		self._validate_positive_prices()

	def _validate_positive_prices(self):
		invalid_prices = [
			{"row": idx, "price_name": price.price_name, "rate": price.rate or 0}
			for idx, price in enumerate(self.prices, start=1)
			if price.rate is not None and price.rate <= 0
		]

		if invalid_prices:
			error_messages = [
				f"Row {item['row']}: <b>{item['price_name']}</b> - Rate must be greater than 0 (currently {item['rate']})"
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
			fields_to_check: List of field names to form a unique key (e.g. ["price_list", "uom"])
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

	def sync_item_prices(self):
		settings = self.get_appointment_settings()

		if not settings.use_erpnext_pricing:
			return

		if not self.item:
			return

		for price_row in self.prices:
			self._sync_single_item_price(price_row)

	def _sync_single_item_price(self, price_row):
		filters = {
			"item_code": self.item,
			"price_list": price_row.price_list,
			"uom": price_row.uom,
		}

		existing_prices = frappe.get_all(
			"Item Price",
			filters=filters,
			fields=["name", "price_list_rate", "valid_from", "valid_upto"],
			order_by="valid_from desc",
		)

		if not existing_prices:
			self._create_item_price(price_row)
			return

		current_date = getdate(today())
		target_price = self._select_best_item_price(existing_prices, current_date)

		if target_price:
			item_price = frappe.get_doc("Item Price", target_price["name"])
			item_price.price_list_rate = price_row.rate
			item_price.save(ignore_permissions=True)

		else:
			self._create_item_price(price_row)

	def _select_best_item_price(self, prices, reference_date):
		"""
		Select the most appropriate Item Price from multiple options based on date validity

		Priority:
		1. Currently valid price (reference_date is within valid_from and valid_upto)
		2. Price with no date restrictions (always valid)

		Args:
			prices: List of Item Price records with valid_from and valid_upto
			reference_date: Date to check validity against

		Returns:
			Selected Item Price record or None
		"""
		current_valid = []
		future_valid = []
		no_date_restriction = []
		expired = []

		for price in prices:
			valid_from = getdate(price.valid_from) if price.valid_from else None
			valid_upto = getdate(price.valid_upto) if price.valid_upto else None

			if not valid_from and not valid_upto:
				no_date_restriction.append(price)
				continue

			is_valid_now = True
			if valid_from and valid_from > reference_date:
				is_valid_now = False
			if valid_upto and valid_upto < reference_date:
				is_valid_now = False

			if is_valid_now:
				current_valid.append(price)
			elif valid_from and valid_from > reference_date:
				future_valid.append(price)
			else:
				expired.append(price)

		if current_valid:
			return max(
				current_valid, key=lambda x: getdate(x.valid_from) if x.valid_from else getdate("1900-01-01")
			)

		if no_date_restriction:
			return no_date_restriction[0]

		return None

	def _create_item_price(self, price_row):
		item_price_doc = frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": self.item,
				"price_list": price_row.price_list,
				"price_list_rate": price_row.rate,
			}
		)
		item_price_doc.insert(ignore_permissions=True)

		frappe.msgprint(
			_("New Item Price <b>{1}</b> created for {0}").format(
				get_link_to_form("Item Price", item_price_doc.name), self.item
			),
			indicator="green",
			alert=True,
		)

	def auto_create_item_if_missing(self):
		settings = self.get_appointment_settings()

		if not settings.auto_create_service_items:
			return

		if self.item and frappe.db.exists("Item", self.item):
			return

		item_name = self.appointment_type

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

	@frappe.whitelist()
	def get_applicable_item_price(self, price_list, uom, date=None):
		"""
		Get the most applicable item price for a given price list and date
		Focuses on date validity (valid_from and valid_upto)
		"""

		if not self.item or not price_list:
			return None

		reference_date = getdate(date) if date else getdate(today())

		# Get all Item Prices for this item and price list
		filters = {"item_code": self.item, "price_list": price_list, "selling": 1, "uom": uom}

		item_prices = frappe.get_all(
			"Item Price",
			filters=filters,
			fields=["name", "price_list_rate", "valid_from", "valid_upto"],
			order_by="valid_from desc",
		)

		if not item_prices:
			return {
				"price_found": False,
				"multiple_prices": False,
			}

		selected_price = self._select_best_item_price(item_prices, reference_date)

		if selected_price:
			return {
				"price_found": True,
				"multiple_prices": False,
				"rate": selected_price.price_list_rate,
				"uom": selected_price.uom,
				"currency": selected_price.currency,
			}

		return {"price_found": False, "multiple_prices": False}
	
	
@frappe.whitelist()
def get_service_cards():
		return frappe.get_all(
		   "Appointment Type",
		filters={
			"disabled": 0
		},
		fields=[
			"appointment_type",
			"description",
			"custom_image",
			"default_duration_in_minutes",
		],
		order_by="creation desc",
			
		
		
		)
