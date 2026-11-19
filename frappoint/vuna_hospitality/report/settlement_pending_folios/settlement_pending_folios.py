# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

"""Settlement Pending Folios: folios whose invoice failed to submit, and why."""

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate

from frappoint.vuna_hospitality.services.hotel_reports import column, report_scope

FOLIO = "Guest Folio"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	scope = report_scope(filters)
	if not scope:
		return [], []
	property_name, business_date = scope
	return get_columns(), get_data(property_name, business_date)


def get_columns():
	return [
		column("folio", "Folio", "Link", 150, FOLIO),
		column("payee_name", "Payee", "Data", 180),
		column("stay", "Stay", "Link", 150, "Stay Reservation"),
		column("house_account", "House Account", "Link", 140, "House Account"),
		column("since", "Pending Since", "Date", 110),
		column("days", "Days", "Int", 70),
		column("balance", "Balance", "Currency", 120, "currency"),
		column("settlement_error", "Why It Failed", "Small Text", 320),
		column("currency", "Currency", "Link", 80, "Currency"),
	]


def get_data(property_name: str, business_date) -> list[dict]:
	rows = frappe.get_all(
		FOLIO,
		filters={"property": property_name, "status": "Settlement Pending"},
		fields=[
			"name as folio",
			"payee_name",
			"stay_reservation as stay",
			"house_account",
			"modified",
			"balance",
			"settlement_error",
			"currency",
		],
		order_by="modified asc",
	)
	for row in rows:
		row.since = getdate(row.modified)
		row.days = max(date_diff(business_date, row.since), 0)
	if rows:
		rows.append(
			{
				"payee_name": _("Total"),
				"balance": flt(sum(flt(row.balance) for row in rows), 2),
				"currency": rows[0].currency,
				"is_total": 1,
			}
		)
	return rows
