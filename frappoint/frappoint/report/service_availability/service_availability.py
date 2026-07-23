# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate

from frappoint.frappoint.services.availability_projector import (
	get_available_slots as get_projected_available_slots,
)


def execute(filters=None):
	"""Main entry point for script report - Service Availability Overview"""
	filters = frappe._dict(filters or {})

	columns = get_columns()
	data = get_data(filters)

	service_unit_names_in_data = set()
	for row in data:
		service_units = row.get("service_units", "")
		for unit in service_units.split(", "):
			if unit:
				service_unit_names_in_data.add(unit)

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
			"label": _("Available Slots"),
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
	service_unit_filter = filters.get("service_unit") or None
	gender = filters.get("gender") or None
	rows = get_projected_available_slots(
		service_type_id=service_type,
		start_date=start_date,
		end_date=end_date,
		provider_id=provider_filter,
		service_unit_id=service_unit_filter,
		required_duration_minutes=duration,
	)

	if gender:
		allowed = set(
			frappe.get_all(
				"Service Provider",
				filters={"gender": gender},
				pluck="name",
			)
		)
		rows = [row for row in rows if row.get("provider") in allowed]

	return [
		{
			"service_type": service_type,
			"date": row.get("date"),
			"start_time": row.get("start_time"),
			"end_time": row.get("end_time"),
			"duration_minutes": row.get("duration") or 0,
			"provider_count": 1,
			"providers": row.get("provider_name") or row.get("provider") or "",
			"service_units": row.get("service_unit_name") or row.get("service_unit") or "",
			"shift_assignments": "",
			"slot_ids_count": 0,
		}
		for row in rows
	]


def _unique_values(values):
	result = []
	for value in values:
		if value and value not in result:
			result.append(value)
	return result
