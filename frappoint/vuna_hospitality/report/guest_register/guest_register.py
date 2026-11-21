# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

"""Guest Register: the statutory register by arrival date. Document numbers are masked; the
Export button (authorized roles) downloads them in full. Every view and export is recorded."""

import frappe
from frappe import _
from frappe.utils import add_days, getdate

from frappoint.vuna_hospitality.services import guest_register
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.hotel_reports import column, report_scope


def execute(filters=None):
	filters = frappe._dict(filters or {})
	scope = report_scope(filters)
	if not scope:
		return [], []
	property_name, business_date = scope
	to_date = getdate(filters.get("to_date") or business_date)
	from_date = getdate(filters.get("from_date") or add_days(to_date, -6))
	rows = guest_register.entries(property_name, from_date, to_date)
	log_event(
		"Hotel Property",
		property_name,
		"Guest Register Viewed",
		data={"from": str(from_date), "to": str(to_date), "entries": len(rows)},
		property_name=property_name,
	)
	return get_columns(), rows


def get_columns():
	return [
		column("arrival_date", "Arrival", "Date", 100),
		column("departure_date", "Departure", "Date", 100),
		column("room_number", "Room", "Data", 70),
		column("full_name", "Name", "Data", 180),
		column("nationality", "Nationality", "Link", 110, "Country"),
		column("nationality_class", "Class", "Data", 85),
		column("id_document_type", "Document", "Data", 110),
		column("id_document_hint", "Number", "Data", 100),
		column("date_of_birth", "Date of Birth", "Date", 105),
		column("arrived_from", "Arrived From", "Data", 130),
		column("next_destination", "Next Destination", "Data", 130),
		column("acceptance_reference", "Acceptance", "Data", 110),
		column("stay_reservation", "Stay", "Link", 150, "Stay Reservation"),
		column("name", "Entry", "Link", 160, "Guest Register Entry"),
	]
