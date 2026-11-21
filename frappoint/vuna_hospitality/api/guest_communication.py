"""Guest messages, traces, and folio emails (feature F20).

Each command checks the stay's (or folio's) property first; the services check the roles.
"""

import frappe
from frappe import _
from frappe.utils import sbool

from frappoint.vuna_hospitality.constants import PERSONAL_DATA_ROLES
from frappoint.vuna_hospitality.services import guest_messages, notifications
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.property_scope import assert_property_access

STAY = "Stay Reservation"


def _stay(stay: str) -> str:
	property_name = frappe.db.get_value(STAY, stay, "property")
	if not property_name:
		raise frappe.DoesNotExistError(_("Stay Reservation {0} does not exist.").format(stay))
	assert_property_access(property_name)
	frappe.has_permission(STAY, "read", stay, throw=True)
	return stay


def _of(doctype: str, name: str) -> str:
	stay = frappe.db.get_value(doctype, name, "stay_reservation")
	if not stay:
		raise frappe.DoesNotExistError(_("{0} {1} does not exist.").format(_(doctype), name))
	return _stay(stay)


def _messages(stay: str) -> dict:
	data = guest_messages.stay_messages(stay)
	data["notifications"] = frappe.get_all(
		notifications.LOG,
		filters={"stay_reservation": stay},
		fields=["name", "event", "channel", "status", "recipient", "sent_at", "error"],
		order_by="sent_at desc",
		limit=20,
	)
	return data


@frappe.whitelist()
@require_hospitality
def get_guest_messages(stay: str) -> dict:
	"""The stay's messages, traces, and the notifications its guests were sent."""
	return _messages(_stay(stay))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def take_message(stay: str, message: str, sender: str | None = None, stay_guest: str | None = None) -> dict:
	guest_messages.take_message(_stay(stay), message, sender, stay_guest or None)
	return _messages(stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def close_message(
	message: str, delivered: int = 1, channel: str = "In Person", notes: str | None = None
) -> dict:
	stay = _of(guest_messages.MESSAGE, message)
	guest_messages.close_message(message, sbool(delivered), channel, notes)
	return _messages(stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def add_trace(stay: str, department: str, due_date: str, text: str, due_time: str | None = None) -> dict:
	guest_messages.add_trace(_stay(stay), department, due_date, text, due_time or None)
	return _messages(stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def close_trace(trace: str, resolved: int = 1, notes: str | None = None) -> dict:
	stay = _of(guest_messages.TRACE, trace)
	guest_messages.close_trace(trace, sbool(resolved), notes)
	return _messages(stay)


@frappe.whitelist()
@require_hospitality
def get_traces_due(property: str, department: str | None = None) -> list[dict]:
	"""Open traces due by the property's business date, for a department or all."""
	assert_property_access(property)
	business_date = frappe.db.get_value("Hotel Property", property, "business_date")
	return guest_messages.traces_due(property, business_date, department or None)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def email_folio(folio: str) -> dict:
	"""Email the folio to its payee by the property's Folio Emailed rules."""
	property_name = frappe.db.get_value("Guest Folio", folio, "property")
	if not property_name:
		raise frappe.DoesNotExistError(_("Guest Folio {0} does not exist.").format(folio))
	assert_property_access(property_name)
	frappe.only_for(PERSONAL_DATA_ROLES)
	frappe.has_permission("Guest Folio", "read", folio, throw=True)
	logs = notifications.email_folio(folio)
	return {
		"logs": frappe.get_all(
			notifications.LOG,
			filters={"name": ["in", logs or [""]]},
			fields=["status", "recipient", "error"],
		)
	}
