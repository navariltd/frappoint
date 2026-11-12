# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

"""Sales Partner commission not billed yet: one row per Sales Invoice, grouped by partner.

The "Create Purchase Invoices" button bills it (see services/partner_commission.py). ERPNext's
Sales Partner Commission Summary remains the history of all commission.
"""

import frappe
from frappe import _

from frappoint.frappoint.services.partner_commission import get_payable_commissions, payable_on


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	if not filters.company:
		return columns(), []
	rows = get_payable_commissions(
		filters.company, filters.to_date, filters.from_date, filters.sales_partner or None
	)
	suppliers = dict(
		frappe.get_all(
			"Sales Partner",
			filters={"name": ["in", list({row.sales_partner for row in rows}) or [""]]},
			fields=["name", "custom_supplier"],
			as_list=True,
		)
	)
	data = [
		{
			"sales_partner": row.sales_partner,
			"supplier": suppliers.get(row.sales_partner),
			"sales_invoice": row.name,
			"posting_date": row.posting_date,
			"customer": row.customer,
			"is_return": row.is_return,
			"amount_eligible_for_commission": row.amount_eligible_for_commission,
			"commission_rate": row.commission_rate,
			"total_commission": row.total_commission,
		}
		for row in sorted(rows, key=lambda r: (r.sales_partner, r.posting_date, r.name))
	]
	message = _("Commission becomes payable on: {0} (Selling Settings).").format(_(payable_on()))
	return columns(), data, message


def columns() -> list[dict]:
	return [
		{
			"fieldname": "sales_partner",
			"label": _("Sales Partner"),
			"fieldtype": "Link",
			"options": "Sales Partner",
			"width": 160,
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 150,
		},
		{
			"fieldname": "sales_invoice",
			"label": _("Sales Invoice"),
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 170,
		},
		{"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 160,
		},
		{"fieldname": "is_return", "label": _("Credit Note"), "fieldtype": "Check", "width": 90},
		{
			"fieldname": "amount_eligible_for_commission",
			"label": _("Eligible Amount"),
			"fieldtype": "Currency",
			"width": 130,
		},
		{"fieldname": "commission_rate", "label": _("Rate (%)"), "fieldtype": "Percent", "width": 80},
		{"fieldname": "total_commission", "label": _("Commission"), "fieldtype": "Currency", "width": 130},
	]
