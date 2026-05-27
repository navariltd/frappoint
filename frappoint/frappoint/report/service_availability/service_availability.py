# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate

from frappoint.frappoint.doctype.service_provider_appointment_slot.service_provider_appointment_slot import (
	get_available_slots,
)


def execute(filters=None):
	"""Main entry point for script report - Service Availability Overview"""
	filters = frappe._dict(filters or {})

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "service_type",
			"label": _("Service Type"),
			"fieldtype": "Link",
			"options": "Service Type",
			"width": 140,
		},
		{
			"fieldname": "date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"fieldname": "start_time",
			"label": _("Start Time"),
			"fieldtype": "Time",
			"width": 90,
		},
		{
			"fieldname": "end_time",
			"label": _("End Time"),
			"fieldtype": "Time",
			"width": 90,
		},
		{
			"fieldname": "duration_minutes",
			"label": _("Duration (Minutes)"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "provider_count",
			"label": _("Available Providers"),
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"fieldname": "providers",
			"label": _("Provider Names"),
			"fieldtype": "Data",
			"width": 240,
		},
		{
			"fieldname": "service_units",
			"label": _("Service Units"),
			"fieldtype": "Data",
			"width": 240,
		},
		{
			"fieldname": "shift_assignments",
			"label": _("Shift Assignments"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "slot_ids_count",
			"label": _("Component Slots"),
			"fieldtype": "Int",
			"width": 100,
		},
	]


def get_data(filters):
	"""Fetch and aggregate service availability data"""
	service_type = filters.get("service_type")
	duration = filters.get("duration")
	if not service_type or not duration:
		return []

	start_date = getdate(filters.get("date_from") or nowdate())
	if filters.get("date_to"):
		end_date = getdate(filters.get("date_to"))
	else:
		end_date = add_days(start_date, int(filters.get("days_ahead") or 30))

	if end_date < start_date:
		end_date = start_date

	provider_filter = filters.get("provider") or None
	gender = filters.get("gender") or None
	rows = []

	for current_date in _date_range(start_date, end_date):
		available_slots = get_available_slots(
			service_type,
			duration,
			provider=provider_filter,
			date=current_date,
			gender=gender,
		)

		for date_group in available_slots:
			date_value = date_group.get("date") or current_date
			for slot in date_group.get("slots", []):
				provider_rows = slot.get("providers") or []
				provider_names = _unique_values(
					provider_row.get("provider_name") or provider_row.get("provider")
					for provider_row in provider_rows
				)
				service_units = _unique_values(
					provider_row.get("service_unit_name") or provider_row.get("service_unit")
					for provider_row in provider_rows
				)
				shift_assignments = _unique_values(
					provider_row.get("shift_assignment") for provider_row in provider_rows
				)
				slot_ids = []
				for provider_row in provider_rows:
					slot_ids.extend(provider_row.get("slot_ids") or [])

				rows.append(
					{
						"service_type": service_type,
						"date": date_value,
						"start_time": slot.get("start_time"),
						"end_time": slot.get("end_time"),
						"duration_minutes": slot.get("duration") or 0,
						"provider_count": len(provider_rows),
						"providers": ", ".join(provider_names),
						"service_units": ", ".join(service_units),
						"shift_assignments": ", ".join(shift_assignments),
						"slot_ids_count": len(slot_ids),
					}
				)

	return rows


def _date_range(start_date, end_date):
	current_date = start_date
	while current_date <= end_date:
		yield current_date
		current_date = add_days(current_date, 1)


def _unique_values(values):
	result = []
	for value in values:
		if value and value not in result:
			result.append(value)
	return result
