# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

"""House Position: rooms available per room type and night, with the counts behind each number."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, cint, formatdate, getdate

from frappoint.vuna_hospitality.services.inventory import get_availability
from frappoint.vuna_hospitality.services.property_scope import assert_property_access

MAX_DAYS = 62
# Breakdown rows shown under each room type, in display order.
BREAKDOWN = (
	("physical_rooms", "Physical Rooms"),
	("out_of_order", "Out of Order"),
	("out_of_service", "Out of Service (still sellable)"),
	("sold", "Sold"),
	("held", "Held"),
	("block_unpicked", "Group Block Unpicked"),
	("overbooking_limit", "Overbooking Limit"),
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("property"):
		return [], []
	assert_property_access(filters.property)

	start = getdate(
		filters.get("from_date") or frappe.db.get_value("Hotel Property", filters.property, "business_date")
	)
	days = min(max(cint(filters.get("days") or 14), 1), MAX_DAYS)
	end = add_days(start, days - 1)
	nights = [add_days(start, offset) for offset in range(days)]

	rows = get_availability(filters.property, start, end, filters.get("room_type"))
	return get_columns(nights), get_data(filters.property, rows, nights, filters.get("show_breakdown"))


def night_field(night) -> str:
	return f"n_{getdate(night).strftime('%Y%m%d')}"


def get_columns(nights):
	columns = [{"fieldname": "label", "label": _("Room Type"), "fieldtype": "Data", "width": 230}]
	for night in nights:
		night = getdate(night)
		columns.append(
			{
				"fieldname": night_field(night),
				"label": f"{_(night.strftime('%a'))} {formatdate(night, 'dd-MM')}",
				"fieldtype": "Int",
				"width": 120,
			}
		)
	return columns


def get_data(property_name, rows, nights, show_breakdown=True):
	names = dict(
		frappe.get_all(
			"Room Type",
			filters={"property": property_name},
			fields=["name", "room_type_name"],
			order_by="sort_order, room_type_name",
			as_list=True,
		)
	)
	by_type = defaultdict(dict)
	for row in rows:
		by_type[row.room_type][getdate(row.inventory_date)] = row

	data = []
	totals = defaultdict(int)
	for room_type, room_type_name in names.items():
		values = by_type.get(room_type, {})
		heading = {
			"label": room_type_name,
			"room_type": room_type,
			"indent": 0,
			"parent_key": None,
			"is_group": 1,
		}
		for night in nights:
			available = cint(values[getdate(night)].available) if getdate(night) in values else 0
			heading[night_field(night)] = available
			totals[night_field(night)] += available
		data.append(heading)

		if cint(show_breakdown):
			for field, label in BREAKDOWN:
				line = {
					"label": _(label),
					"room_type": room_type,
					"indent": 1,
					"parent_key": room_type,
					"is_group": 0,
				}
				for night in nights:
					row = values.get(getdate(night))
					line[night_field(night)] = cint(row[field]) if row else 0
				data.append(line)

	if names:
		data.append({"label": _("Total Available"), "indent": 0, "parent_key": None, "is_total": 1, **totals})
	return data
