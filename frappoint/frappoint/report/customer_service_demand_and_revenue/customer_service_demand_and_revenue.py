# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import getdate

STATUSES = (
	"Open",
	"Pending Payment",
	"Confirmed",
	"Checked In",
	"In Progress",
	"Rescheduled",
	"Completed",
	"Closed",
	"No Show",
)


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	data = get_data(filters)
	return get_columns(), get_customer_hierarchy(data), None, get_chart(data, filters.currency)


def validate_filters(filters):
	for field, label in (("company", "Company"), ("from_date", "From Date"), ("to_date", "To Date")):
		if not filters.get(field):
			frappe.throw(_("{0} is required").format(_(label)))
	filters.from_date, filters.to_date = getdate(filters.from_date), getdate(filters.to_date)
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be after To Date"))
	if filters.get("status") and filters.status not in STATUSES:
		frappe.throw(_("Select a non-cancelled appointment status"))
	filters.currency = filters.get("currency") or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	if not filters.currency:
		frappe.throw(_("Currency is required"))


def get_columns():
	return [
		{"label": _("Customer / Service"), "fieldname": "label", "fieldtype": "Data", "width": 240},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 180,
		},
		{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 180},
		{
			"label": _("Service Type"),
			"fieldname": "service_type",
			"fieldtype": "Link",
			"options": "Service Type",
			"width": 180,
		},
		{
			"label": _("Appointments Requested"),
			"fieldname": "appointments_requested",
			"fieldtype": "Int",
			"width": 180,
		},
		{
			"label": _("Completed Appointments"),
			"fieldname": "completed_appointments",
			"fieldtype": "Int",
			"width": 180,
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 90,
		},
		{
			"label": _("Revenue"),
			"fieldname": "revenue",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 160,
		},
	]


def get_data(filters):
	"""Count appointments once, respecting permissions; accrue completed grand totals."""
	conditions = {
		"company": filters.company,
		"currency": filters.currency,
		"docstatus": ["<", 2],
		"status": ["!=", "Cancelled"],
		"appointment_date": ["between", [filters.from_date, filters.to_date]],
		"customer": ["is", "set"],
		"appointment_type": ["is", "set"],
	}
	for field, source in (
		("customer", "customer"),
		("appointment_type", "service_type"),
		("status", "status"),
	):
		if filters.get(source):
			conditions[field] = filters[source]
	appointments = frappe.get_list(
		"Service Appointment",
		filters=conditions,
		fields=["customer", "full_name", "appointment_type", "status", "grand_total"],
		limit_page_length=0,
		order_by="customer asc, appointment_type asc",
	)
	rows = {}
	for appointment in appointments:
		key = (appointment.customer, appointment.appointment_type)
		if key not in rows:
			rows[key] = dict(
				customer=key[0],
				customer_name=appointment.full_name or "",
				service_type=key[1],
				appointments_requested=0,
				completed_appointments=0,
				currency=filters.currency,
				revenue=Decimal("0"),
			)
		row = rows[key]
		row["appointments_requested"] += 1
		if appointment.status == "Completed":
			row["completed_appointments"] += 1
			row["revenue"] += Decimal(str(appointment.grand_total or 0))
	for row in rows.values():
		row["revenue"] = float(row["revenue"])
	return list(rows.values())


def get_customer_hierarchy(data):
	groups = {}
	for row in data:
		groups.setdefault(row["customer"], []).append(row)
	result = []
	for customer, children in groups.items():
		heading = {
			"label": children[0]["customer_name"] or customer,
			"customer": customer,
			"customer_name": children[0]["customer_name"],
			"currency": children[0]["currency"],
			"indent": 0,
			"is_customer_total": True,
			"parent_customer": None,
			"appointments_requested": sum(row["appointments_requested"] for row in children),
			"completed_appointments": sum(row["completed_appointments"] for row in children),
			"revenue": float(sum((Decimal(str(row["revenue"])) for row in children), Decimal("0"))),
		}
		result.append(heading)
		result.extend(
			{**row, "label": row["service_type"], "indent": 1, "parent_customer": customer}
			for row in children
		)
	return result


def get_chart(data, currency):
	totals = {}
	for row in data:
		customer = row["customer"]
		totals[customer] = totals.get(customer, Decimal("0")) + Decimal(str(row["revenue"]))
	# Pie charts cannot represent negative contributions.
	if any(value < 0 for value in totals.values()):
		return None
	ranked = sorted(
		((customer, value) for customer, value in totals.items() if value > 0),
		key=lambda item: (-item[1], item[0]),
	)
	if not ranked:
		return None
	labels = [customer for customer, _value in ranked[:10]]
	values = [float(value) for _customer, value in ranked[:10]]
	if len(ranked) > 10:
		labels.append(_("Others"))
		values.append(float(sum((value for _customer, value in ranked[10:]), Decimal("0"))))
	return {
		"title": _("Revenue by Customer") + f" ({currency})",
		"type": "pie",
		"data": {"labels": labels, "datasets": [{"name": _("Revenue"), "values": values}]},
	}
