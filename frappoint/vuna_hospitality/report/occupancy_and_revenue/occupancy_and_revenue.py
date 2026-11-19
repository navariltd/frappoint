# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

"""Occupancy and Revenue: rooms available and sold, occupancy %, ADR and RevPAR per night.

The definitions are in services/hotel_reports.py, shared with night audit's stored report, so the
two always agree.
"""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate

from frappoint.vuna_hospitality.services import hotel_reports
from frappoint.vuna_hospitality.services.hotel_reports import column, report_scope

MAX_DAYS = 366


def execute(filters=None):
	filters = frappe._dict(filters or {})
	scope = report_scope(filters)
	if not scope:
		return [], []
	property_name, business_date = scope
	end = getdate(filters.get("to_date") or add_days(business_date, -1))
	start = getdate(filters.get("from_date") or add_days(end, -29))
	if date_diff(end, start) >= MAX_DAYS:
		frappe.throw(_("Choose at most {0} nights.").format(MAX_DAYS))
	money = hotel_reports.currency(property_name)
	rows = hotel_reports.occupancy(property_name, start, end)
	total = hotel_reports.total_metrics(rows, money)
	total.update(date=None, label=_("Total"), is_total=1)
	data = [{**row, "label": frappe.format(row["date"], "Date")} for row in rows] + [total]
	return get_columns(money), data, None, get_chart(rows), get_summary(total, money)


def get_columns(money: str):
	return [
		column("label", "Night", "Data", 110),
		column("rooms_available", "Rooms Available", "Int", 120),
		column("rooms_sold", "Rooms Sold", "Int", 100),
		column("complimentary", "Complimentary", "Int", 110),
		column("occupancy", "Occupancy %", "Percent", 110),
		column("room_revenue", "Room Revenue", "Currency", 140, "currency"),
		column("adr", "ADR", "Currency", 120, "currency"),
		column("revpar", "RevPAR", "Currency", 120, "currency"),
		column("currency", "Currency", "Link", 80, "Currency"),
	]


def get_chart(rows):
	return {
		"data": {
			"labels": [frappe.format(row["date"], "Date") for row in rows],
			"datasets": [{"name": _("Occupancy %"), "values": [row["occupancy"] for row in rows]}],
		},
		"type": "line",
	}


def get_summary(total: dict, money: str):
	currency = {"fieldtype": "Currency", "options": money}
	return [
		{"label": _("Occupancy"), "value": total["occupancy"], "datatype": "Percent", "indicator": "blue"},
		{
			"label": _("ADR"),
			"value": total["adr"],
			"datatype": "Currency",
			"currency": money,
			"indicator": "green",
		},
		{
			"label": _("RevPAR"),
			"value": total["revpar"],
			"datatype": "Currency",
			"currency": money,
			"indicator": "green",
		},
		{
			"label": _("Room Revenue"),
			"value": frappe.format(total["room_revenue"], currency),
			"datatype": "Data",
		},
	]
