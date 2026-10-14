# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from datetime import timedelta
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import add_months, getdate

RANGES = ("Weekly", "Monthly", "Quarterly", "Yearly")
METRICS = (
	("completed_appointments", "Completed Appointments", "Int"),
	("total_revenue", "Total Revenue", "Currency"),
	("average_revenue", "Average Revenue per Treatment", "Currency"),
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	periods = get_periods(filters)
	return get_columns(periods), get_data(filters, periods)


def validate_filters(filters):
	for field, label in (("from_date", "From Date"), ("to_date", "To Date")):
		if not filters.get(field):
			frappe.throw(_("{0} is required").format(_(label)))
		filters[field] = getdate(filters[field])
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be after To Date"))
	filters.range = filters.get("range") or "Monthly"
	if filters.range not in RANGES:
		frappe.throw(_("Range must be Weekly, Monthly, Quarterly or Yearly"))


def period_start(date, frequency):
	date = getdate(date)
	if frequency == "Weekly":
		return date - timedelta(days=date.weekday())
	month = date.month
	if frequency == "Quarterly":
		month = ((month - 1) // 3) * 3 + 1
	elif frequency == "Yearly":
		month = 1
	return date.replace(month=month, day=1)


def get_periods(filters):
	"""Calendar periods; the query keeps partial periods inside the exact date filters."""
	periods = []
	start = period_start(filters.from_date, filters.range)
	while start <= filters.to_date:
		if filters.range == "Weekly":
			year, week, _weekday = start.isocalendar()
			label = _("Week {0} {1}").format(week, year)
			next_start = start + timedelta(days=7)
		else:
			months = {"Monthly": 1, "Quarterly": 3, "Yearly": 12}[filters.range]
			next_start = getdate(add_months(start, months))
			if filters.range == "Monthly":
				label = _(start.strftime("%b")) + f" {start.year}"
			elif filters.range == "Quarterly":
				label = _("Quarter {0} {1}").format((start.month - 1) // 3 + 1, start.year)
			else:
				label = str(start.year)
		periods.append({"key": f"period_{start:%Y%m%d}", "label": label, "start": start})
		start = next_start
	return periods


def get_columns(periods):
	columns = [
		{"label": _("Treatment"), "fieldname": "treatment", "fieldtype": "Link",
		 "options": "Service Type", "width": 200},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link",
		 "options": "Currency", "width": 90},
	]
	for prefix, label in [("", ""), *((p["key"] + "_", p["label"]) for p in periods)]:
		for metric, metric_label, fieldtype in METRICS:
			column = {"label": f"{label}: {_(metric_label)}" if label else _(metric_label),
				"fieldname": prefix + metric, "fieldtype": fieldtype, "width": 180}
			if fieldtype == "Currency":
				column["options"] = "currency"
			columns.append(column)
	return columns


def get_data(filters, periods):
	"""Use permission-aware appointments, without joining guests or payments (which duplicates revenue)."""
	conditions = {
		"status": "Completed",
		"docstatus": ["<", 2],
		"appointment_date": ["between", [filters.from_date, filters.to_date]],
	}
	if filters.get("company"):
		conditions["company"] = filters.company
	appointments = frappe.get_list(
		"Service Appointment", filters=conditions,
		fields=["appointment_type", "appointment_date", "currency", "grand_total"],
		limit_page_length=0, order_by="appointment_type asc, currency asc, appointment_date asc",
	)
	rows = {}
	for appointment in appointments:
		key = (appointment.appointment_type, appointment.currency)
		if key not in rows:
			row = {"treatment": key[0], "currency": key[1]}
			for prefix in ["", *(p["key"] + "_" for p in periods)]:
				row[prefix + "completed_appointments"] = 0
				row[prefix + "total_revenue"] = Decimal("0")
				row[prefix + "average_revenue"] = Decimal("0")
			rows[key] = row
		row = rows[key]
		start = period_start(appointment.appointment_date, filters.range)
		for prefix in ("", f"period_{start:%Y%m%d}_"):
			row[prefix + "completed_appointments"] += 1
			row[prefix + "total_revenue"] += Decimal(str(appointment.grand_total or 0))
	for row in rows.values():
		for prefix in ["", *(p["key"] + "_" for p in periods)]:
			count = row[prefix + "completed_appointments"]
			revenue = row[prefix + "total_revenue"]
			row[prefix + "average_revenue"] = float(revenue / count) if count else 0
			row[prefix + "total_revenue"] = float(revenue)
	return list(rows.values())
