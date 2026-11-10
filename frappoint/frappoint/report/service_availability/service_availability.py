# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from collections import OrderedDict
from datetime import time

import frappe
from frappe import _
from frappe.utils import add_days, format_time, formatdate, get_time, getdate, nowdate

from frappoint.frappoint.services.availability_projector import (
	get_available_slots as get_projected_available_slots,
)

# Tree levels: a date, the start times on that date, then each provider/unit option at that time.
DATE_LEVEL, TIME_LEVEL, OPTION_LEVEL = 0, 1, 2


def execute(filters=None):
	"""Service Availability: open booking windows for a service, grouped by date and start time."""
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	options = get_options(filters)
	return get_columns(), build_tree(options)


def validate_filters(filters):
	start_from, start_to = filters.get("start_time_from"), filters.get("start_time_to")
	if start_from and start_to and get_time(start_from) > get_time(start_to):
		frappe.throw(_("Start Time From cannot be later than Start Time To."))


def get_columns():
	return [
		{
			"fieldname": "label",
			"label": _("Date / Start Time / Provider"),
			"fieldtype": "Data",
			"width": 260,
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
			"fieldname": "available_options",
			"label": _("Available Options"),
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "provider_count",
			"label": _("Available Providers"),
			"fieldtype": "Int",
			"width": 120,
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
			"width": 220,
		},
		{
			"fieldname": "service_unit_capacity",
			"label": _("Service Unit Capacity"),
			"fieldtype": "Int",
			"width": 140,
		},
		{
			"fieldname": "service_type",
			"label": _("Service Type"),
			"fieldtype": "Link",
			"options": "Service Type",
			"width": 140,
		},
	]


def get_date_range(filters):
	start_date = getdate(filters.get("date_from") or nowdate())
	if filters.get("date_to"):
		end_date = getdate(filters.get("date_to"))
	else:
		end_date = getdate(add_days(start_date, int(filters.get("days_ahead") or 30)))
	return start_date, max(start_date, end_date)


def get_options(filters):
	"""Return one row per bookable option (date, start time, provider, unit) matching the filters."""
	service_type = filters.get("service_type")
	duration = filters.get("duration")
	if not service_type or not duration:
		return []

	start_date, end_date = get_date_range(filters)
	rows = get_projected_available_slots(
		service_type_id=service_type,
		start_date=start_date,
		end_date=end_date,
		provider_id=filters.get("provider") or None,
		service_unit_id=filters.get("service_unit") or None,
		required_duration_minutes=duration,
	)

	rows = filter_by_start_time(rows, filters.get("start_time_from"), filters.get("start_time_to"))

	if filters.get("gender"):
		allowed = set(frappe.get_all("Service Provider", filters={"gender": filters.gender}, pluck="name"))
		rows = [row for row in rows if row.get("provider") in allowed]

	capacities = get_service_unit_capacities(rows)
	return [
		{
			"service_type": service_type,
			"date": getdate(row.get("date")),
			"start_time": _as_time(row.get("start_time")),
			"end_time": _as_time(row.get("end_time")),
			"duration_minutes": row.get("duration") or 0,
			"provider": row.get("provider"),
			"provider_name": row.get("provider_name") or row.get("provider") or "",
			"service_unit": row.get("service_unit"),
			"service_unit_name": row.get("service_unit_name") or row.get("service_unit") or "",
			"service_unit_capacity": capacities.get(row.get("service_unit")),
		}
		for row in rows
	]


def filter_by_start_time(rows, start_time_from=None, start_time_to=None):
	"""Keep rows whose start time is within [from, to]. Either bound may be empty."""
	lower = get_time(start_time_from) if start_time_from else None
	upper = get_time(start_time_to) if start_time_to else None
	if not lower and not upper:
		return rows

	kept = []
	for row in rows:
		start = _as_time(row.get("start_time"))
		if start is None:
			continue
		if lower and start < lower:
			continue
		if upper and start > upper:
			continue
		kept.append(row)
	return kept


def get_service_unit_capacities(rows):
	unit_ids = sorted({row.get("service_unit") for row in rows if row.get("service_unit")})
	if not unit_ids:
		return {}
	return {
		unit.name: unit.capacity
		for unit in frappe.get_all(
			"Service Unit", filters={"name": ["in", unit_ids]}, fields=["name", "capacity"]
		)
	}


def build_tree(options):
	"""Group options into Date -> Start Time -> Provider/Unit rows for a tree report.

	Each row carries `indent` and `parent_key`; group rows summarise their children.
	"""
	by_date = OrderedDict()
	for option in sorted(
		options, key=lambda row: (row["date"], row["start_time"] or time.min, row["provider_name"])
	):
		by_date.setdefault(option["date"], OrderedDict()).setdefault(option["start_time"], []).append(option)

	tree = []
	for day, times in by_date.items():
		day_key = f"date:{day}"
		day_options = [option for group in times.values() for option in group]
		tree.append(
			{
				**summarise(day_options),
				"key": day_key,
				"parent_key": None,
				"indent": DATE_LEVEL,
				"label": f"{_(day.strftime('%a'))}, {formatdate(day)}",
				"date": day,
				"start_time": min(times),
				"end_time": max(option["end_time"] for option in day_options),
				"is_group": 1,
			}
		)

		for start, group in times.items():
			time_key = f"{day_key}|time:{start}"
			tree.append(
				{
					**summarise(group),
					"key": time_key,
					"parent_key": day_key,
					"indent": TIME_LEVEL,
					"label": format_time(start, "HH:mm"),
					"date": day,
					"start_time": start,
					"end_time": max(option["end_time"] for option in group),
					"is_group": 1,
				}
			)
			tree.extend(
				{
					**option,
					"key": f"{time_key}|{option['provider']}|{option['service_unit'] or ''}",
					"parent_key": time_key,
					"indent": OPTION_LEVEL,
					"label": " · ".join(
						part for part in (option["provider_name"], option["service_unit_name"]) if part
					),
					"available_options": 1,
					"provider_count": 1,
					"providers": option["provider_name"],
					"service_units": option["service_unit_name"],
					"is_group": 0,
				}
				for option in group
			)
	return tree


def summarise(options):
	"""Totals shown on a date or start-time row."""
	providers = _unique(option["provider_name"] for option in options)
	units = _unique(option["service_unit_name"] for option in options)
	capacities = {
		option["service_unit"]: option["service_unit_capacity"]
		for option in options
		if option["service_unit"] and option["service_unit_capacity"]
	}
	return {
		"service_type": options[0]["service_type"],
		"duration_minutes": options[0]["duration_minutes"],
		"available_options": len(options),
		"provider_count": len({option["provider"] for option in options if option["provider"]}),
		"providers": ", ".join(providers),
		"service_units": ", ".join(units),
		"service_unit_capacity": sum(capacities.values()) if capacities else None,
	}


def _unique(values):
	result = []
	for value in values:
		if value and value not in result:
			result.append(value)
	return result


def _as_time(value):
	if value is None or value == "":
		return None
	return value if isinstance(value, time) else get_time(value)
