"""Tax on folio lines, computed by ERPNext itself (design §25.2; feature F9).

The PMS has no tax rates or tax arithmetic of its own. A line's tax comes from:

- the property's **Sales Taxes and Charges Template** (Hotel Property `sales_taxes_template`), and
- the Item's **Item Tax Template**, which overrides the rate per tax account, as on any invoice.

`compute()` builds an unsaved Sales Invoice with one line and runs ERPNext's
`calculate_taxes_and_totals` on it. The settlement invoice (F11) is built the same way from the
same Items and template, so the folio and the invoice can't disagree.

A tax-inclusive price sets "Included in Basic Rate" on the template's percentage rows, so ERPNext
back-calculates the net and the tax, and net plus tax equals the price exactly. An exclusive price
adds the tax on top. Fixed ("Actual") and per-quantity rows can't be included in a price, so they
always add on top.
"""

from dataclasses import dataclass, field
from decimal import Decimal

import frappe
from frappe.model import child_table_fields, default_fields
from frappe.utils import flt, getdate

from frappoint.vuna_hospitality.services.money import from_minor, to_minor

# Template rows that can be part of a tax-inclusive price.
INCLUSIVE_CHARGE_TYPES = ("On Net Total", "On Previous Row Amount", "On Previous Row Total")


@dataclass
class TaxResult:
	net_minor: int
	tax_minor: int
	gross_minor: int
	breakdown: list[dict] = field(default_factory=list)

	def as_amounts(self, currency: str) -> dict:
		return {
			"net_amount": from_minor(self.net_minor, currency),
			"tax_amount": from_minor(self.tax_minor, currency),
			"gross_amount": from_minor(self.gross_minor, currency),
		}


def property_tax_settings(property_name: str) -> frappe._dict:
	return frappe.db.get_value(
		"Hotel Property",
		property_name,
		["company", "currency", "sales_taxes_template", "prices_include_tax"],
		as_dict=True,
	)


def item_tax_template(item: str, on_date=None) -> str | None:
	"""The Item's Item Tax Template (latest valid one without a tax category), else its group's."""
	on_date = getdate(on_date)
	for parenttype, parent in (
		("Item", item),
		("Item Group", frappe.db.get_value("Item", item, "item_group")),
	):
		rows = frappe.get_all(
			"Item Tax",
			filters={"parenttype": parenttype, "parent": parent},
			fields=["item_tax_template", "tax_category", "valid_from"],
			order_by="valid_from desc",
		)
		for row in rows:
			if not row.tax_category and (not row.valid_from or getdate(row.valid_from) <= on_date):
				return row.item_tax_template
	return None


# ERPNext's whitelisted get_item_tax_map and get_taxes_and_charges check that the session user may
# select the template. Working out a hotel price is trusted server work that front-desk and revenue
# staff run without access to tax setup, so these read the templates directly, as ERPNext does
# behind those checks.

NOT_APPLICABLE_TAX = "N/A"  # erpnext.stock.get_item_details.NOT_APPLICABLE_TAX


def item_tax_map(template: str | None, company: str) -> dict:
	"""{tax account: rate} of an Item Tax Template, for the company's accounts."""
	if not template:
		return {}
	rates = {}
	for row in frappe.get_cached_doc("Item Tax Template", template).taxes:
		if frappe.get_cached_value("Account", row.tax_type, "company") == company:
			rates[row.tax_type] = NOT_APPLICABLE_TAX if row.get("not_applicable") else row.tax_rate
	return rates


def template_taxes(template: str) -> list[dict]:
	"""The tax rows of a Sales Taxes and Charges Template, ready to append to an invoice."""
	rows = []
	for tax in frappe.get_cached_doc("Sales Taxes and Charges Template", template).get("taxes"):
		row = tax.as_dict()
		for fieldname in (*default_fields, *child_table_fields):
			row.pop(fieldname, None)
		rows.append(row)
	return rows


def compute(
	property_name: str,
	item: str | None,
	amount,
	*,
	inclusive: bool,
	quantity=1,
	on_date=None,
) -> TaxResult:
	"""Tax on `amount` (the line total) of `item` at the property.

	With `inclusive`, `amount` is the gross and is split into net and tax; otherwise it is the net
	and the tax is added. Lines without an Item, or a property without a template and an Item without
	an Item Tax Template, carry no tax.
	"""
	return compute_lines(property_name, [(item, amount, quantity)], inclusive=inclusive, on_date=on_date)


def compute_lines(property_name: str, lines, *, inclusive: bool, on_date=None) -> TaxResult:
	"""Tax on several (item, line total, quantity) lines at once, as one invoice would charge it."""
	settings = property_tax_settings(property_name)
	currency = settings.currency
	lines = [(item, to_minor(amount, currency), flt(quantity) or 1) for item, amount, quantity in lines]
	amount_minor = sum(minor for _item, minor, _qty in lines)
	no_tax = TaxResult(amount_minor, 0, amount_minor)
	taxed = [(item, minor, qty) for item, minor, qty in lines if item and minor > 0]
	templates = {item: item_tax_template(item, on_date) for item, _minor, _qty in taxed}
	if not taxed or (not settings.sales_taxes_template and not any(templates.values())):
		return no_tax

	invoice = frappe.new_doc("Sales Invoice")
	invoice.update(
		{
			"company": settings.company,
			"currency": currency,
			"conversion_rate": 1,
			"price_list_currency": currency,
			"plc_conversion_rate": 1,
			"posting_date": getdate(on_date),
		}
	)
	for item, minor, quantity in taxed:
		rate = float(Decimal(str(from_minor(minor, currency))) / Decimal(str(quantity)))
		template = templates[item]
		invoice.append(
			"items",
			{
				"item_code": item,
				"qty": quantity,
				"rate": rate,
				"price_list_rate": rate,
				"conversion_factor": 1,
				"item_tax_template": template,
				"item_tax_rate": frappe.as_json(item_tax_map(template, settings.company)),
			},
		)
	if settings.sales_taxes_template:
		for row in template_taxes(settings.sales_taxes_template):
			row["included_in_print_rate"] = int(
				bool(inclusive) and row.get("charge_type") in INCLUSIVE_CHARGE_TYPES
			)
			invoice.append("taxes", row)
	invoice.calculate_taxes_and_totals()

	untaxed_minor = amount_minor - sum(minor for _item, minor, _qty in taxed)
	tax_minor = to_minor(invoice.total_taxes_and_charges, currency)
	gross_minor = to_minor(invoice.grand_total, currency) + untaxed_minor
	if inclusive and not any(row.charge_type in ("Actual", "On Item Quantity") for row in invoice.taxes):
		# ERPNext puts any rounding difference into the last tax row; the gross is the price.
		gross_minor = amount_minor
	breakdown = [
		{"account": row.account_head, "description": row.description, "amount": flt(row.tax_amount)}
		for row in invoice.taxes
		if flt(row.tax_amount)
	]
	return TaxResult(gross_minor - tax_minor, tax_minor, gross_minor, breakdown)
