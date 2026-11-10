"""Write entries to the append-only Hospitality Event Log."""

from typing import Any

import frappe
from frappe.utils import now_datetime

from frappoint.vuna_hospitality.constants import EVENT_LOG_DOCTYPE, PROPERTY_DOCTYPE, PROPERTY_FIELD


def log_event(
	reference_doctype: str,
	reference_name: str,
	event_type: str,
	*,
	from_status: str | None = None,
	to_status: str | None = None,
	reason: str | None = None,
	data: dict[str, Any] | None = None,
	property_name: str | None = None,
	business_date=None,
):
	"""Append one audit entry and return it.

	`property_name` and `business_date` default to the referenced document's property and that
	property's current business date, when both exist.
	"""
	if property_name is None:
		property_name = _get_property(reference_doctype, reference_name)
	if business_date is None and property_name and frappe.db.exists("DocType", PROPERTY_DOCTYPE):
		business_date = frappe.db.get_value(PROPERTY_DOCTYPE, property_name, "business_date")

	entry = frappe.get_doc(
		{
			"doctype": EVENT_LOG_DOCTYPE,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"event_type": event_type,
			"from_status": from_status,
			"to_status": to_status,
			"reason": reason,
			"data": frappe.as_json(data) if data else None,
			"property": property_name,
			"business_date": business_date,
			"user": frappe.session.user,
			"roles": ", ".join(sorted(set(frappe.get_roles()) - {"All", "Guest"})),
			"timestamp": now_datetime(),
			"request_id": _request_id(),
		}
	)
	entry.insert(ignore_permissions=True)
	return entry


def _get_property(reference_doctype: str, reference_name: str) -> str | None:
	meta = frappe.get_meta(reference_doctype)
	if meta.issingle or not meta.has_field(PROPERTY_FIELD):
		return None
	return frappe.db.get_value(reference_doctype, reference_name, PROPERTY_FIELD)


def _request_id() -> str | None:
	request = getattr(frappe.local, "request", None)
	if request is not None:
		return getattr(frappe.local, "request_id", None) or request.headers.get("X-Frappe-Request-Id")
	job = getattr(frappe.local, "job", None)
	return getattr(job, "id", None) if job else None
