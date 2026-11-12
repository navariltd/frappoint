"""Pay Sales Partner commission through Accounts Payable.

ERPNext calculates a partner's commission on each Sales Invoice (`sales_partner`, `commission_rate`,
`total_commission`) but never turns it into a payable: a Sales Partner isn't a Supplier, and the
commission reports create no entries. Following ERPNext's documented flow, this module:

1. links each Sales Partner to the Supplier that is paid (`Sales Partner.custom_supplier`),
2. finds the commission not billed yet, and
3. bills it to that Supplier as a draft Purchase Invoice, one row per Sales Invoice, which finance
   reviews, submits and pays with a normal Payment Entry.

Each billed Sales Invoice records the Purchase Invoice in `custom_commission_purchase_invoice`, so
its commission is never billed twice. Cancelling or deleting that Purchase Invoice clears the mark.
Commission becomes payable when the Sales Invoice is paid in full or as soon as it is submitted,
per Selling Settings > Sales Partner Commission.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.utils import flt, getdate, nowdate

SALES_INVOICE = "Sales Invoice"
PURCHASE_INVOICE = "Purchase Invoice"
SETTINGS = "Selling Settings"

BILLED_FIELD = "custom_commission_purchase_invoice"
SUPPLIER_FIELD = "custom_supplier"
PAID_INVOICES, SUBMITTED_INVOICES = "Paid Invoices", "Submitted Invoices"


class CommissionPayoutError(frappe.ValidationError):
	"""Commission can't be billed: no Supplier, no commission Item, or nothing to bill."""


# --------------------------------------------------------------------------- partner -> supplier


def ensure_partner_supplier(sales_partner: str) -> str:
	"""The Supplier paid this partner's commission, creating and linking one if needed.

	A Supplier with the partner's name is linked rather than duplicated. Safe to call again.
	"""
	partner = frappe.get_doc("Sales Partner", sales_partner)
	if partner.get(SUPPLIER_FIELD):
		return partner.get(SUPPLIER_FIELD)

	supplier = frappe.db.get_value("Supplier", {"supplier_name": partner.partner_name}, "name")
	if not supplier:
		supplier = (
			frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": partner.partner_name,
					"supplier_type": "Company",
					"supplier_group": _supplier_group(),
				}
			)
			.insert()
			.name
		)
	partner.db_set(SUPPLIER_FIELD, supplier)
	return supplier


def _supplier_group() -> str | None:
	return (
		frappe.db.get_single_value(SETTINGS, "custom_commission_supplier_group")
		or frappe.db.get_single_value("Buying Settings", "supplier_group")
		or frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
	)


# --------------------------------------------------------------------------- what is payable


def payable_on() -> str:
	return frappe.db.get_single_value(SETTINGS, "custom_commission_payable_on") or PAID_INVOICES


def get_payable_commissions(
	company: str,
	to_date=None,
	from_date=None,
	sales_partner: str | None = None,
	for_update: bool = False,
	sales_invoices: list[str] | None = None,
) -> list[dict]:
	"""Submitted Sales Invoices whose partner commission hasn't been billed yet, oldest first.

	Credit notes are included (their commission is negative) so they reduce the payout. With
	"Paid Invoices", an invoice counts only once nothing is outstanding on it.
	"""
	invoice = frappe.qb.DocType(SALES_INVOICE)
	query = (
		frappe.qb.from_(invoice)
		.select(
			invoice.name,
			invoice.sales_partner,
			invoice.posting_date,
			invoice.customer,
			invoice.customer_name,
			invoice.is_return,
			invoice.amount_eligible_for_commission,
			invoice.commission_rate,
			invoice.total_commission,
			invoice.outstanding_amount,
		)
		.where(invoice.docstatus == 1)
		.where(invoice.company == company)
		.where(invoice.sales_partner.isnotnull() & (invoice.sales_partner != ""))
		.where(invoice.total_commission != 0)
		.where(invoice[BILLED_FIELD].isnull() | (invoice[BILLED_FIELD] == ""))
		.where(invoice.posting_date <= getdate(to_date or nowdate()))
		.orderby(invoice.posting_date, order=Order.asc)
		.orderby(invoice.name, order=Order.asc)
	)
	if from_date:
		query = query.where(invoice.posting_date >= getdate(from_date))
	if sales_partner:
		query = query.where(invoice.sales_partner == sales_partner)
	if sales_invoices is not None:
		# Only the invoices the user picked; any no longer payable simply drop out.
		query = query.where(invoice.name.isin(list(sales_invoices) or [""]))
	if payable_on() == PAID_INVOICES:
		query = query.where(invoice.outstanding_amount <= 0)
	if for_update:
		query = query.for_update()
	return query.run(as_dict=True)


def summarize_by_partner(rows: list[dict]) -> list[dict]:
	"""Totals per partner, with the partner's linked Supplier."""
	totals: dict = defaultdict(lambda: {"invoices": 0, "commission": 0.0})
	for row in rows:
		totals[row.sales_partner]["invoices"] += 1
		totals[row.sales_partner]["commission"] += flt(row.total_commission)
	suppliers = dict(
		frappe.get_all(
			"Sales Partner",
			filters={"name": ["in", list(totals) or [""]]},
			fields=["name", SUPPLIER_FIELD],
			as_list=True,
		)
	)
	return [
		{"sales_partner": partner, "supplier": suppliers.get(partner), **values}
		for partner, values in sorted(totals.items())
	]


# --------------------------------------------------------------------------- billing


def make_commission_purchase_invoice(
	sales_partner: str,
	company: str,
	to_date=None,
	from_date=None,
	sales_invoices: list[str] | None = None,
) -> str:
	"""Bill a partner's unbilled commission to its Supplier as a draft Purchase Invoice.

	`sales_invoices` limits the bill to those invoices (they must still be payable). The Sales
	Invoices are locked while they are billed, so two users can't bill them twice. Returns the
	Purchase Invoice name.
	"""
	supplier = frappe.db.get_value("Sales Partner", sales_partner, SUPPLIER_FIELD)
	if not supplier:
		frappe.throw(
			_("Sales Partner {0} has no Supplier. Create or link one before billing its commission.").format(
				frappe.bold(sales_partner)
			),
			CommissionPayoutError,
		)
	item = frappe.db.get_single_value(SETTINGS, "custom_commission_item")
	if not item:
		frappe.throw(
			_("Set the Commission Item in Selling Settings > Sales Partner Commission."),
			CommissionPayoutError,
		)

	rows = get_payable_commissions(
		company, to_date, from_date, sales_partner, for_update=True, sales_invoices=sales_invoices
	)
	total = sum(flt(row.total_commission) for row in rows)
	if not rows or total <= 0:
		frappe.throw(
			_("Sales Partner {0} has no commission to bill for {1} up to {2}.").format(
				frappe.bold(sales_partner), company, frappe.format(getdate(to_date or nowdate()), "Date")
			),
			CommissionPayoutError,
		)

	company_currency = frappe.get_cached_value("Company", company, "default_currency")
	price_list = _buying_price_list(company_currency)
	default_price_list = frappe.db.get_single_value("Buying Settings", "buying_price_list")
	if not price_list and default_price_list:
		# ERPNext would fall back to this default and reject it as disabled or in another currency.
		frappe.throw(
			_(
				"No enabled buying Price List in {0}. Enable {1} or create a buying Price List in {0} before billing commission."
			).format(company_currency, frappe.bold(default_price_list)),
			CommissionPayoutError,
		)
	purchase_invoice = frappe.new_doc(PURCHASE_INVOICE)
	purchase_invoice.update(
		{
			"supplier": supplier,
			"company": company,
			"posting_date": nowdate(),
			"bill_date": nowdate(),
			"currency": company_currency,
			"conversion_rate": 1,
			"update_stock": 0,
			# Commission rates come from the Sales Invoices, not prices. Name an enabled buying
			# price list so ERPNext doesn't fall back to a default that may be disabled.
			"buying_price_list": price_list,
			"price_list_currency": company_currency,
			"plc_conversion_rate": 1,
			"ignore_pricing_rule": 1,
			"remarks": _("Sales Partner commission for {0}: {1} invoice(s) up to {2}.").format(
				sales_partner, len(rows), getdate(to_date or nowdate())
			),
		}
	)
	for row in rows:
		purchase_invoice.append(
			"items",
			{
				"item_code": item,
				"qty": 1,
				"rate": flt(row.total_commission),
				"description": _("Commission on {0} ({1}, {2})").format(
					row.name, row.customer_name or row.customer, row.posting_date
				),
			},
		)
	purchase_invoice.set_missing_values()
	purchase_invoice.insert()

	invoice = frappe.qb.DocType(SALES_INVOICE)
	(
		frappe.qb.update(invoice)
		.set(invoice[BILLED_FIELD], purchase_invoice.name)
		.where(invoice.name.isin([row.name for row in rows]))
	).run()
	return purchase_invoice.name


def _buying_price_list(currency: str) -> str | None:
	"""An enabled buying price list in `currency`, preferring the Buying Settings default."""
	default = frappe.db.get_single_value("Buying Settings", "buying_price_list")
	if default and frappe.db.get_value(
		"Price List", {"name": default, "enabled": 1, "buying": 1, "currency": currency}
	):
		return default
	return frappe.db.get_value("Price List", {"enabled": 1, "buying": 1, "currency": currency}, "name")


def make_all_commission_purchase_invoices(
	company: str, to_date=None, from_date=None, sales_invoices: list[str] | None = None
) -> dict:
	"""One draft Purchase Invoice per partner with commission to bill.

	With `sales_invoices`, only those invoices are billed (grouped by their partner); ones that are
	not payable (unpaid under "Paid Invoices", already billed, or another company's) are skipped.

	Partners without a Supplier, or whose bill fails, are reported instead of stopping the others.
	"""
	created, skipped = [], []
	payable = get_payable_commissions(company, to_date, from_date, sales_invoices=sales_invoices)
	if sales_invoices is not None:
		found = {row.name for row in payable}
		skipped.extend(
			{"sales_invoice": name, "reason": _("Not payable: unpaid, already billed, or another company's.")}
			for name in sales_invoices
			if name not in found
		)
	for summary in summarize_by_partner(payable):
		partner = summary["sales_partner"]
		if summary["commission"] <= 0:
			skipped.append({"sales_partner": partner, "reason": _("Nothing to bill after credit notes.")})
			continue
		if not summary["supplier"]:
			skipped.append({"sales_partner": partner, "reason": _("No Supplier linked.")})
			continue
		frappe.db.savepoint("commission_payout")
		try:
			created.append(
				{
					"sales_partner": partner,
					"purchase_invoice": make_commission_purchase_invoice(
						partner, company, to_date, from_date, sales_invoices
					),
					"commission": summary["commission"],
				}
			)
		except frappe.ValidationError as error:
			frappe.db.rollback(save_point="commission_payout")
			skipped.append({"sales_partner": partner, "reason": str(error)})
	return {"created": created, "skipped": skipped}


def release_commission_invoices(doc, method=None) -> None:
	"""Purchase Invoice cancelled or deleted: its Sales Invoices' commission is payable again."""
	if not frappe.get_meta(SALES_INVOICE).has_field(BILLED_FIELD):
		return
	invoice = frappe.qb.DocType(SALES_INVOICE)
	(
		frappe.qb.update(invoice).set(invoice[BILLED_FIELD], None).where(invoice[BILLED_FIELD] == doc.name)
	).run()
