"""The statutory guest register: reveal a document number, and export the register (feature F20).

Both are recorded in the event log. Reading the masked register is the Guest Register report.
"""

import frappe
from frappe import _
from frappe.utils import getdate

from frappoint.vuna_hospitality.services import guest_register
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.property_scope import assert_property_access

EXPORT_COLUMNS = (
	("arrival_date", "Arrival"),
	("departure_date", "Departure"),
	("room_number", "Room"),
	("full_name", "Name"),
	("nationality", "Nationality"),
	("id_document_type", "Document Type"),
	("id_document_number", "Document Number"),
	("date_of_birth", "Date of Birth"),
	("arrived_from", "Arrived From"),
	("next_destination", "Next Destination"),
	("acceptance_reference", "Acceptance Reference"),
	("stay_reservation", "Stay"),
)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def reveal_document_number(entry: str) -> dict:
	"""The full document number on one register entry, for an authorized role. Recorded."""
	property_name = frappe.db.get_value(guest_register.ENTRY, entry, "property")
	if not property_name:
		raise frappe.DoesNotExistError(_("Guest Register Entry {0} does not exist.").format(entry))
	assert_property_access(property_name)
	return guest_register.reveal(entry)


@frappe.whitelist()
@require_hospitality
def export_guest_register(property: str, from_date: str, to_date: str) -> None:
	"""Download the register with full document numbers as CSV. Recorded with who and the range."""
	assert_property_access(property)
	if getdate(from_date) > getdate(to_date):
		frappe.throw(_("The start date is after the end date."))
	rows = guest_register.export(property, from_date, to_date)
	frappe.response["type"] = "csv"
	frappe.response["doctype"] = f"Guest Register {property} {getdate(from_date)} to {getdate(to_date)}"
	frappe.response["result"] = [
		[_(label) for _field, label in EXPORT_COLUMNS],
		*[[row.get(field) or "" for field, _label in EXPORT_COLUMNS] for row in rows],
	]
