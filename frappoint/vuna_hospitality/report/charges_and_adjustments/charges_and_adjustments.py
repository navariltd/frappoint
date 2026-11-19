# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

"""Charges and Adjustments: every folio line posted in a period, filterable to reversals, manual
postings, or adjustments, write-offs and paid-outs, with who posted it and why."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from frappoint.vuna_hospitality.services.hotel_reports import column, report_scope

TRANSACTION = "Folio Transaction"
KINDS = ("All charges", "Reversals", "Manual postings", "Adjustments, write-offs and paid-outs")
CHARGE_TYPES = ("Revenue", "Adjustment", "Write-off", "Paid-out", "Allowance")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	scope = report_scope(filters)
	if not scope:
		return [], []
	property_name, business_date = scope
	to_date = getdate(filters.get("to_date") or business_date)
	from_date = getdate(filters.get("from_date") or add_days(to_date, -6))
	kind = filters.get("kind") if filters.get("kind") in KINDS else KINDS[0]
	return get_columns(), get_data(property_name, from_date, to_date, kind, filters.get("charge_code"))


def get_columns():
	return [
		column("transaction", "Line", "Link", 170, TRANSACTION),
		column("business_date", "Business Date", "Date", 105),
		column("posting_datetime", "Posted At", "Datetime", 150),
		column("guest_folio", "Folio", "Link", 145, "Guest Folio"),
		column("room_number_snapshot", "Room", "Data", 65),
		column("charge_code", "Charge Code", "Link", 120, "Charge Code"),
		column("description_snapshot", "Description", "Data", 190),
		column("transaction_type", "Type", "Data", 95),
		column("net_amount", "Net", "Currency", 110, "currency"),
		column("tax_amount", "Tax", "Currency", 100, "currency"),
		column("gross_amount", "Gross", "Currency", 115, "currency"),
		column("is_manual", "Manual", "Check", 70),
		column("reverses", "Reverses", "Link", 160, TRANSACTION),
		column("reason", "Reason", "Data", 180),
		column("owner", "Posted By", "Link", 160, "User"),
		column("currency", "Currency", "Link", 80, "Currency"),
	]


def _filters(property_name: str, from_date, to_date, kind: str, charge_code: str | None) -> dict:
	filters = {
		"property": property_name,
		"docstatus": 1,
		"business_date": ["between", [from_date, to_date]],
		"transaction_type": ["in", CHARGE_TYPES],
	}
	if kind == "Reversals":
		filters["reverses"] = ["is", "set"]
	elif kind == "Manual postings":
		filters["is_manual"] = 1
	elif kind == KINDS[3]:
		filters["transaction_type"] = ["in", ("Adjustment", "Write-off", "Paid-out")]
	if charge_code:
		filters["charge_code"] = charge_code
	return filters


def get_data(property_name: str, from_date, to_date, kind: str, charge_code: str | None = None) -> list[dict]:
	rows = frappe.get_all(
		TRANSACTION,
		filters=_filters(property_name, from_date, to_date, kind, charge_code),
		fields=[
			"name as transaction",
			"business_date",
			"posting_datetime",
			"guest_folio",
			"room_number_snapshot",
			"charge_code",
			"description_snapshot",
			"transaction_type",
			"direction",
			"net_amount",
			"tax_amount",
			"gross_amount",
			"is_manual",
			"reverses",
			"reason",
			"owner",
			"currency",
		],
		order_by="business_date asc, posting_datetime asc",
	)
	for row in rows:
		# Credits (reversals, allowances, write-offs) reduce what the guest owes: show them negative.
		if row.direction == "Credit":
			for field in ("net_amount", "tax_amount", "gross_amount"):
				row[field] = -flt(row[field])
		row.transaction_type = _(row.transaction_type)
	if rows:
		rows.append(
			{
				"description_snapshot": _("Total"),
				**{
					field: flt(sum(flt(row[field]) for row in rows), 2)
					for field in ("net_amount", "tax_amount", "gross_amount")
				},
				"currency": rows[0].currency,
				"is_total": 1,
			}
		)
	return rows
