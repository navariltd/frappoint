# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Count, Sum
from frappe.utils import add_months, cint, getdate, today

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	filters.view = filters.get("view") or "Weekly"
	start, end = validate_dates(filters)
	periods = get_periods(filters.view, start, end)
	return get_columns(filters.view, periods), get_data(filters, start, end, periods)


def validate_dates(filters):
	if filters.view not in ("Weekly", "Monthly"):
		frappe.throw(_("View must be Weekly or Monthly"))
	if filters.view == "Weekly":
		if not filters.get("week_start"):
			frappe.throw(_("Week Start is required"))
		start = getdate(filters.week_start)
		return start, start + timedelta(days=6)
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required"))
	start, end = getdate(filters.from_date), getdate(filters.to_date)
	if start > end:
		frappe.throw(_("From Date cannot be after To Date"))
	if start < getdate(add_months(today(), -12)):
		frappe.throw(_("From Date cannot be more than 12 months ago"))
	return start, end


def get_periods(view, start, end):
	if view == "Weekly":
		return [
			{
				"key": DAYS[(start.weekday() + index) % 7].lower(),
				"label": f"{_(DAYS[(start.weekday() + index) % 7])} ({start + timedelta(days=index):%d %b})",
				"start": start + timedelta(days=index),
				"end": start + timedelta(days=index + 1),
			}
			for index in range(7)
		]
	first = start.replace(day=1)
	month_count = (end.year - first.year) * 12 + end.month - first.month + 1
	return [
		{
			"key": f"month_{month:%Y%m}",
			"label": _(month.strftime("%b")) + f" {month.year}",
			"start": month,
			"end": getdate(add_months(month, 1)),
		}
		for month in (getdate(add_months(first, index)) for index in range(month_count))
	]


def get_columns(view, periods) -> list[dict]:
	return [
		{
			"label": _("Service Type"),
			"fieldname": "service_type",
			"fieldtype": "Link",
			"options": "Service Type",
			"width": 220,
		},
		{
			"label": _("Weekly Total") if view == "Weekly" else _("Period Total"),
			"fieldname": "weekly_total" if view == "Weekly" else "period_total",
			"fieldtype": "Int",
			"width": 140,
		},
		*[
			{"label": period["label"], "fieldname": period["key"], "fieldtype": "Int", "width": 150}
			for period in periods
		],
	]


def get_data(filters, start, end, periods) -> list[dict]:
	"""Count each qualifying appointment once, with period aggregation in the database."""
	appointment = frappe.qb.DocType("Service Appointment")
	conditions = {
		"docstatus": ["<", 2],
		"status": ["!=", "Cancelled"],
		"appointment_date": ["between", [start, end]],
		"appointment_type": ["is", "set"],
	}
	if filters.get("company"):
		conditions["company"] = filters.company
	if filters.get("service_type"):
		conditions["appointment_type"] = filters.service_type
	if cint(filters.get("is_completed")):
		conditions["status"] = "Completed"

	return (
		frappe.qb.get_query(
			"Service Appointment",
			fields=[
				appointment.appointment_type.as_("service_type"),
				*[
					Sum(
						Case()
						.when(
							(appointment.appointment_date >= period["start"])
							& (appointment.appointment_date < period["end"]),
							1,
						)
						.else_(0)
					).as_(period["key"])
					for period in periods
				],
				Count(appointment.name).as_("weekly_total" if filters.view == "Weekly" else "period_total"),
			],
			filters=conditions,
			group_by="appointment_type",
			order_by="appointment_type asc",
			ignore_permissions=False,
		)
		.where(appointment.status.isin(["Confirmed", "Completed"]) | (appointment.payment_status == "Paid"))
		.run(as_dict=True)
	)
