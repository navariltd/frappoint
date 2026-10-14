# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	return get_columns(), get_data(filters)


def validate_filters(filters):
	for field, label in (("from_date", "From Date"), ("to_date", "To Date")):
		if not filters.get(field):
			frappe.throw(_("{0} is required").format(_(label)))
		filters[field] = getdate(filters[field])
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be after To Date"))


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Service Provider"),
			"fieldname": "service_provider",
			"fieldtype": "Link",
			"options": "Service Provider",
			"width": 180,
		},
		{
			"label": _("Provider Name"),
			"fieldname": "provider_name",
			"fieldtype": "Data",
			"width": 200,
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
			"label": _("Total Revenue"),
			"fieldname": "total_revenue",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 180,
		},
	]


def get_data(filters) -> list[dict]:
	"""Accrued revenue is discounted grand total, counted once per completed appointment.

	Use appointment dates and respect appointment permissions. Keep currencies separate
	and omit appointments without an assigned provider.
	"""
	conditions = {
		"status": "Completed",
		"docstatus": ["<", 2],
		"appointment_date": ["between", [filters.from_date, filters.to_date]],
		"appointment_provider": ["is", "set"],
	}
	if filters.get("company"):
		conditions["company"] = filters.company
	if filters.get("service_provider"):
		conditions["appointment_provider"] = filters.service_provider
	appointments = frappe.get_list(
		"Service Appointment",
		filters=conditions,
		fields=["appointment_provider", "service_provider_name", "currency", "grand_total"],
		limit_page_length=0,
		order_by="appointment_provider asc, currency asc",
	)
	rows = {}
	for appointment in appointments:
		key = (appointment.appointment_provider, appointment.currency)
		if key not in rows:
			rows[key] = {
				"service_provider": key[0],
				"provider_name": appointment.service_provider_name or "",
				"currency": key[1],
				"completed_appointments": 0,
				"total_revenue": Decimal("0"),
			}
		row = rows[key]
		row["completed_appointments"] += 1
		row["total_revenue"] += Decimal(str(appointment.grand_total or 0))
		if not row["provider_name"]:
			row["provider_name"] = appointment.service_provider_name or ""
	for row in rows.values():
		row["total_revenue"] = float(row["total_revenue"])
	return list(rows.values())
