# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

"""Front Desk Movements: arrivals, departures, in-house guests, no-shows or cancellations for a date."""

import frappe
from frappe import _
from frappe.utils import add_days, getdate

from frappoint.vuna_hospitality.services.hotel_reports import column, report_scope, stay_rooms

STAY = "Stay Reservation"
LISTS = ("Arrivals", "Departures", "In House", "No Shows", "Cancellations")
NOT_EXPECTED = ("Held", "Cancelled", "Expired", "No Show")
STAYED = ("In House", "Due Out", "Checked Out")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	scope = report_scope(filters)
	if not scope:
		return [], []
	property_name, business_date = scope
	day = getdate(filters.get("date") or business_date)
	kind = filters.get("list") if filters.get("list") in LISTS else "Arrivals"
	return get_columns(), get_data(property_name, day, kind)


def get_columns():
	return [
		column("stay", "Stay", "Link", 150, STAY),
		column("guest", "Guest", "Data", 180),
		column("room", "Room", "Data", 70),
		column("room_type", "Room Type", "Link", 130, "Room Type"),
		column("arrival_date", "Arrival", "Date", 100),
		column("departure_date", "Departure", "Date", 100),
		column("nights", "Nights", "Int", 70),
		column("adults", "Adults", "Int", 70),
		column("children", "Children", "Int", 75),
		column("status", "Status", "Data", 100),
		column("rate_plan", "Rate Plan", "Link", 120, "Rate Plan"),
		column("hotel_booking", "Booking", "Link", 140, "Hotel Booking"),
	]


def _filters(property_name: str, day, kind: str) -> dict:
	base = {"property": property_name}
	if kind == "Arrivals":
		return {**base, "arrival_date": day, "status": ["not in", NOT_EXPECTED]}
	if kind == "Departures":
		return {**base, "departure_date": day, "status": ["in", STAYED]}
	if kind == "In House":
		return {**base, "arrival_date": ["<=", day], "departure_date": [">", day], "status": ["in", STAYED]}
	if kind == "No Shows":
		return {**base, "arrival_date": day, "status": "No Show"}
	# Cancellations by the calendar day they were made on.
	return {**base, "status": "Cancelled", "cancelled_at": ["between", [day, add_days(day, 1)]]}


def get_data(property_name: str, day, kind: str) -> list[dict]:
	rows = frappe.get_all(
		STAY,
		filters=_filters(property_name, day, kind),
		fields=[
			"name as stay",
			"lead_guest_name as guest",
			"room_type",
			"arrival_date",
			"departure_date",
			"nights",
			"adults",
			"children",
			"status",
			"rate_plan",
			"hotel_booking",
		],
		order_by="lead_guest_name asc",
	)
	rooms = stay_rooms([row.stay for row in rows])
	for row in rows:
		row["room"] = rooms.get(row.stay)
		row["status"] = _(row.status)
	return rows
