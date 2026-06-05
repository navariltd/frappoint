from __future__ import annotations

import frappe
from frappe.utils import getdate


def sync_leave_application_unavailability(doc, method: str | None = None):
	"""Sync HRMS Leave Application into provider unavailability.

	Leave Application is the HR source of truth. Frappoint stores a local
	unavailability record so the availability projector has one source to read.
	"""
	if not frappe.db.table_exists("Service Provider Unavailability"):
		return

	employee = getattr(doc, "employee", None)
	if not employee:
		return

	provider = frappe.db.get_value("Service Provider", {"employee": employee, "active": 1}, "name")
	if not provider:
		return

	if method == "on_cancel" or getattr(doc, "docstatus", 0) == 2:
		_cancel_leave_unavailability(doc.name)
		return

	status = getattr(doc, "status", None)
	docstatus = int(getattr(doc, "docstatus", 0) or 0)
	if status and status != "Approved":
		_cancel_leave_unavailability(doc.name)
		return
	if docstatus != 1:
		return

	from_date = getattr(doc, "from_date", None)
	to_date = getattr(doc, "to_date", None)
	if not from_date or not to_date:
		return

	existing = frappe.db.get_value(
		"Service Provider Unavailability",
		{"source_doctype": "Leave Application", "source_name": doc.name},
		"name",
	)
	values = {
		"provider": provider,
		"employee": employee,
		"from_date": getdate(from_date),
		"to_date": getdate(to_date),
		"all_day": 1,
		"status": "Active",
		"reason": "Leave",
		"source": "HRMS Leave Application",
		"source_doctype": "Leave Application",
		"source_name": doc.name,
		"notes": _leave_notes(doc),
	}

	if existing:
		unavailability = frappe.get_doc("Service Provider Unavailability", existing)
		if unavailability.docstatus == 1:
			unavailability.cancel()
			unavailability = frappe.get_doc({"doctype": "Service Provider Unavailability", **values})
			unavailability.insert(ignore_permissions=True)
			unavailability.submit()
		else:
			unavailability.update(values)
			unavailability.save(ignore_permissions=True)
			unavailability.submit()
	else:
		unavailability = frappe.get_doc({"doctype": "Service Provider Unavailability", **values})
		unavailability.insert(ignore_permissions=True)
		unavailability.submit()


def _cancel_leave_unavailability(leave_application_name: str):
	existing = frappe.db.get_value(
		"Service Provider Unavailability",
		{
			"source_doctype": "Leave Application",
			"source_name": leave_application_name,
			"status": "Active",
		},
		"name",
	)
	if not existing:
		return

	unavailability = frappe.get_doc("Service Provider Unavailability", existing)
	if unavailability.docstatus == 1:
		unavailability.cancel()
	elif unavailability.docstatus == 0:
		unavailability.status = "Cancelled"
		unavailability.save(ignore_permissions=True)


def _leave_notes(doc) -> str:
	parts = []
	leave_type = getattr(doc, "leave_type", None)
	if leave_type:
		parts.append(f"Leave Type: {leave_type}")

	description = getattr(doc, "description", None)
	if description:
		parts.append(str(description))

	return "\n".join(parts)
