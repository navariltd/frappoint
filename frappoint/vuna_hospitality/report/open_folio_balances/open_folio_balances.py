# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

"""Open Folio Balances: money still owed (or owed back) on folios whose guest has gone, by age."""

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, getdate

from frappoint.vuna_hospitality.services import hotel_reports
from frappoint.vuna_hospitality.services.hotel_reports import column, report_scope
from frappoint.vuna_hospitality.services.money import to_minor

FOLIO = "Guest Folio"
STAY = "Stay Reservation"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	scope = report_scope(filters)
	if not scope:
		return [], []
	property_name, business_date = scope
	return get_columns(), get_data(property_name, business_date, cint(filters.get("min_days")))


def get_columns():
	return [
		column("folio", "Folio", "Link", 150, FOLIO),
		column("payee_name", "Payee", "Data", 180),
		column("group", "Ledger", "Data", 140),
		column("stay", "Stay", "Link", 150, STAY),
		column("since", "Owing Since", "Date", 110),
		column("days", "Days", "Int", 70),
		column("post_stay_until", "Post-stay Until", "Date", 120),
		column("status", "Folio Status", "Data", 130),
		column("balance", "Balance", "Currency", 120, "currency"),
		column("currency", "Currency", "Link", 80, "Currency"),
	]


def get_data(property_name: str, business_date, min_days: int = 0) -> list[dict]:
	folios = frappe.get_all(
		FOLIO,
		filters={"property": property_name, "status": ["in", hotel_reports.POSTABLE_FOLIO_STATUSES]},
		fields=[
			"name as folio",
			"payee_name",
			"status",
			"owner_type",
			"stay_reservation as stay",
			"balance",
			"currency",
			"post_stay_until",
			"creation",
		],
	)
	stays = {
		row.name: row
		for row in frappe.get_all(
			STAY,
			filters={"name": ["in", [row.stay for row in folios if row.stay] or [""]]},
			fields=["name", "status", "departure_date"],
		)
	}
	rows = []
	for row in folios:
		if not to_minor(row.balance, row.currency):
			continue
		stay = stays.get(row.stay) or frappe._dict()
		row.group = hotel_reports.ledger_group(row, stay.get("status"))
		if row.group in (_("In house"), _("Before arrival")):
			continue
		row.since = getdate(stay.get("departure_date") or row.creation)
		row.days = max(date_diff(business_date, row.since), 0)
		row.status = _(row.status)
		if row.days >= min_days:
			rows.append(row)
	rows.sort(key=lambda row: -row.days)
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
