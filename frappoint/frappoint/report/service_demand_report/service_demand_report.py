# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Count, Sum
from frappe.utils import getdate

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	if not filters.get("week_start"):
		frappe.throw(_("Week Start is required"))
	selected_date = getdate(filters.week_start)
	week_start = selected_date - timedelta(days=selected_date.weekday())
	return get_columns(week_start), get_data(filters, week_start)


def get_columns(week_start) -> list[dict]:
	return [
		{
			"label": _("Service Type"),
			"fieldname": "service_type",
			"fieldtype": "Link",
			"options": "Service Type",
			"width": 220,
		},
		{"label": _("Weekly Total"), "fieldname": "weekly_total", "fieldtype": "Int", "width": 140},
		*[
			{
				"label": f"{_(day)} ({week_start + timedelta(days=index):%d %b})",
				"fieldname": day.lower(),
				"fieldtype": "Int",
				"width": 150,
			}
			for index, day in enumerate(DAYS)
		],
	]


def get_data(filters, week_start) -> list[dict]:
	"""Count each qualifying appointment once, with daily aggregation in the database."""
	appointment = frappe.qb.DocType("Service Appointment")
	conditions = {
		"docstatus": ["<", 2],
		"status": ["!=", "Cancelled"],
		"appointment_date": ["between", [week_start, week_start + timedelta(days=6)]],
		"appointment_type": ["is", "set"],
	}
	if filters.get("company"):
		conditions["company"] = filters.company
	if filters.get("service_type"):
		conditions["appointment_type"] = filters.service_type

	return (
		frappe.qb.get_query(
			"Service Appointment",
			fields=[
				appointment.appointment_type.as_("service_type"),
				*[
					Sum(
						Case()
						.when(appointment.appointment_date == week_start + timedelta(days=index), 1)
						.else_(0)
					).as_(day.lower())
					for index, day in enumerate(DAYS)
				],
				Count(appointment.name).as_("weekly_total"),
			],
			filters=conditions,
			group_by="appointment_type",
			order_by="appointment_type asc",
			ignore_permissions=False,
		)
		.where(
			appointment.status.isin(["Confirmed", "Completed"])
			| (appointment.payment_status == "Paid")
		)
		.run(as_dict=True)
	)
