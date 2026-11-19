# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

"""Guest Ledger: every open folio and what it holds, grouped as night audit's control totals are."""

import frappe
from frappe import _
from frappe.utils import flt

from frappoint.vuna_hospitality.services import hotel_reports
from frappoint.vuna_hospitality.services.hotel_reports import column, report_scope, stay_rooms

FOLIO = "Guest Folio"
STAY = "Stay Reservation"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	scope = report_scope(filters)
	if not scope:
		return [], []
	return get_columns(), get_data(scope[0], filters.get("group"))


def get_columns():
	return [
		column("group", "Ledger", "Data", 140),
		column("folio", "Folio", "Link", 150, FOLIO),
		column("payee_name", "Payee", "Data", 180),
		column("stay", "Stay", "Link", 150, STAY),
		column("room", "Room", "Data", 70),
		column("arrival_date", "Arrival", "Date", 100),
		column("departure_date", "Departure", "Date", 100),
		column("status", "Folio Status", "Data", 130),
		column("debits", "Charges", "Currency", 120, "currency"),
		column("credits", "Payments and Credits", "Currency", 150, "currency"),
		column("balance", "Balance", "Currency", 120, "currency"),
		column("currency", "Currency", "Link", 80, "Currency"),
	]


def get_data(property_name: str, group: str | None = None) -> list[dict]:
	folios = frappe.get_all(
		FOLIO,
		filters={"property": property_name, "status": ["in", hotel_reports.POSTABLE_FOLIO_STATUSES]},
		fields=[
			"name as folio",
			"status",
			"owner_type",
			"stay_reservation as stay",
			"payee_name",
			"posted_debits as debits",
			"posted_credits as credits",
			"balance",
			"currency",
		],
	)
	stays = {
		row.name: row
		for row in frappe.get_all(
			STAY,
			filters={"name": ["in", [row.stay for row in folios if row.stay] or [""]]},
			fields=["name", "status", "arrival_date", "departure_date"],
		)
	}
	rooms = stay_rooms(list(stays))
	rows = []
	for row in folios:
		stay = stays.get(row.stay) or frappe._dict()
		row.group = hotel_reports.ledger_group(row, stay.get("status"))
		row.status = _(row.status)
		row.arrival_date, row.departure_date = stay.get("arrival_date"), stay.get("departure_date")
		row.room = rooms.get(row.stay)
		if not group or row.group == _(group):
			rows.append(row)
	rows.sort(key=lambda row: (row.group, row.payee_name or ""))
	if rows:
		rows.append(
			{
				"group": _("Total"),
				"debits": flt(sum(flt(row.debits) for row in rows), 2),
				"credits": flt(sum(flt(row.credits) for row in rows), 2),
				"balance": flt(sum(flt(row.balance) for row in rows), 2),
				"currency": rows[0].currency,
				"is_total": 1,
			}
		)
	return rows
