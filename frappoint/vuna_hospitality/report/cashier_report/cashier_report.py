# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

"""Cashier Report: each shift by mode of payment, with what the drawer should hold, what was
counted, and the variance. An open shift's expected totals stay hidden (blind close)."""

import frappe
from frappe import _
from frappe.utils import add_days, getdate

from frappoint.vuna_hospitality.services import cashiering
from frappoint.vuna_hospitality.services.hotel_reports import column, report_scope

SHIFT = "Cashier Shift"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	scope = report_scope(filters)
	if not scope:
		return [], []
	property_name, business_date = scope
	to_date = getdate(filters.get("to_date") or business_date)
	from_date = getdate(filters.get("from_date") or add_days(to_date, -6))
	return get_columns(), get_data(property_name, from_date, to_date, filters.get("cashier"))


def get_columns():
	return [
		column("shift", "Shift", "Link", 150, SHIFT),
		column("cashier", "Cashier", "Link", 170, "User"),
		column("business_date", "Business Date", "Date", 110),
		column("status", "Status", "Data", 90),
		column("mode_of_payment", "Mode of Payment", "Link", 150, "Mode of Payment"),
		column("expected", "Expected", "Currency", 120, "currency"),
		column("declared", "Counted", "Currency", 120, "currency"),
		column("variance", "Variance", "Currency", 120, "currency"),
		column("variance_reason", "Reason", "Data", 200),
		column("currency", "Currency", "Link", 80, "Currency"),
	]


def get_data(property_name: str, from_date, to_date, cashier: str | None = None) -> list[dict]:
	filters = {"property": property_name, "business_date": ["between", [from_date, to_date]]}
	if cashier:
		filters["cashier"] = cashier
	rows = []
	for shift in frappe.get_all(
		SHIFT,
		filters=filters,
		fields=["name", "cashier", "business_date", "status", "currency"],
		order_by="business_date asc, opened_at asc",
	):
		base = {
			"shift": shift.name,
			"cashier": shift.cashier,
			"business_date": shift.business_date,
			"status": _(shift.status),
			"currency": shift.currency,
		}
		if shift.status == "Open":
			modes = sorted(cashiering.expected_totals(shift.name)) or [None]
			rows += [{**base, "mode_of_payment": mode} for mode in modes]
			continue
		for count in frappe.get_all(
			"Cashier Shift Count",
			filters={"parent": shift.name, "parenttype": SHIFT},
			fields=["mode_of_payment", "expected", "declared", "variance", "variance_reason"],
			order_by="idx asc",
		):
			rows.append({**base, **count})
	return rows
