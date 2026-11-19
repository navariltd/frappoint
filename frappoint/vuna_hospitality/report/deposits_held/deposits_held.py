# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

"""Deposits Held: every open deposit with what was asked, received, refunded and is held now."""

import frappe
from frappe import _
from frappe.utils import flt

from frappoint.vuna_hospitality.services import deposits
from frappoint.vuna_hospitality.services.hotel_reports import column, report_scope
from frappoint.vuna_hospitality.services.money import from_minor

DEPOSIT = "Guest Deposit"
OPEN_STATUSES = ("Requested", "Partly Paid", "Received")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	scope = report_scope(filters)
	if not scope:
		return [], []
	statuses = [filters.status] if filters.get("status") else list(OPEN_STATUSES)
	return get_columns(), get_data(scope[0], statuses)


def get_columns():
	return [
		column("deposit", "Deposit", "Link", 150, DEPOSIT),
		column("stay", "Stay", "Link", 150, "Stay Reservation"),
		column("guest", "Guest", "Data", 170),
		column("arrival_date", "Arrival", "Date", 100),
		column("status", "Status", "Data", 100),
		column("due_date", "Due", "Date", 100),
		column("required", "Required", "Currency", 120, "currency"),
		column("received", "Received", "Currency", 120, "currency"),
		column("refunded", "Refunded", "Currency", 120, "currency"),
		column("held", "Held", "Currency", 120, "currency"),
		column("currency", "Currency", "Link", 80, "Currency"),
	]


def get_data(property_name: str, statuses: list[str]) -> list[dict]:
	rows = frappe.get_all(
		DEPOSIT,
		filters={"property": property_name, "status": ["in", statuses]},
		fields=[
			"name as deposit",
			"stay_reservation as stay",
			"status",
			"due_date",
			"required_amount as required",
			"currency",
		],
		order_by="due_date asc",
	)
	stays = {
		row.name: row
		for row in frappe.get_all(
			"Stay Reservation",
			filters={"name": ["in", [row.stay for row in rows if row.stay] or [""]]},
			fields=["name", "lead_guest_name", "arrival_date"],
		)
	}
	totals = {"required": 0.0, "received": 0.0, "refunded": 0.0, "held": 0.0}
	for row in rows:
		amounts = deposits.amounts(row.deposit)
		stay = stays.get(row.stay) or frappe._dict()
		row.guest, row.arrival_date = stay.get("lead_guest_name"), stay.get("arrival_date")
		row.received = from_minor(amounts.received, row.currency)
		row.refunded = from_minor(amounts.refunded, row.currency)
		row.held = from_minor(amounts.held, row.currency)
		row.status = _(row.status)
		for field in totals:
			totals[field] += row[field] or 0
	if rows:
		totals = {field: flt(value, 2) for field, value in totals.items()}
		rows.append(
			{"deposit": None, "guest": _("Total"), **totals, "currency": rows[0].currency, "is_total": 1}
		)
	return rows
