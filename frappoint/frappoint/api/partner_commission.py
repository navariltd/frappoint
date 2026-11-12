"""Endpoints for billing Sales Partner commission to the partner's Supplier."""

import json

import frappe
from frappe import _

from frappoint.frappoint.services import partner_commission as service


def _check_can_bill() -> None:
	frappe.has_permission("Purchase Invoice", "create", throw=True)


@frappe.whitelist(methods=["POST"])
def create_partner_supplier(sales_partner: str) -> str:
	"""Link the partner to a Supplier, creating one with the partner's name if none exists."""
	frappe.has_permission("Sales Partner", "write", doc=sales_partner, throw=True)
	if not frappe.db.get_value("Sales Partner", sales_partner, service.SUPPLIER_FIELD):
		frappe.has_permission("Supplier", "create", throw=True)
	return service.ensure_partner_supplier(sales_partner)


@frappe.whitelist()
def get_partner_commission_summary(sales_partner: str) -> list[dict]:
	"""Unbilled commission for one partner, per company (for the Sales Partner form)."""
	frappe.has_permission("Sales Partner", "read", doc=sales_partner, throw=True)
	_check_can_bill()
	summary = []
	for company in frappe.get_all("Company", pluck="name"):
		rows = service.get_payable_commissions(company, sales_partner=sales_partner)
		if rows:
			summary.append(
				{
					"company": company,
					"currency": frappe.get_cached_value("Company", company, "default_currency"),
					"invoices": len(rows),
					"commission": sum(row.total_commission for row in rows),
				}
			)
	return summary


@frappe.whitelist(methods=["POST"])
def create_commission_invoice(
	sales_partner: str, company: str, to_date: str | None = None, from_date: str | None = None
) -> str:
	"""Bill one partner's unbilled commission as a draft Purchase Invoice. Returns its name."""
	_check_can_bill()
	return service.make_commission_purchase_invoice(sales_partner, company, to_date, from_date)


@frappe.whitelist(methods=["POST"])
def create_all_commission_invoices(
	company: str,
	to_date: str | None = None,
	from_date: str | None = None,
	sales_invoices: str | list[str] | None = None,
) -> dict:
	"""Bill unbilled commission: one draft Purchase Invoice per partner.

	With `sales_invoices` (a list, or its JSON), only those Sales Invoices are billed.
	"""
	_check_can_bill()
	if not company:
		frappe.throw(_("Choose a company."))
	if isinstance(sales_invoices, str):
		sales_invoices = json.loads(sales_invoices) if sales_invoices.strip() else None
	if sales_invoices is not None and not sales_invoices:
		frappe.throw(_("Select at least one Sales Invoice."))
	return service.make_all_commission_purchase_invoices(company, to_date, from_date, sales_invoices)
