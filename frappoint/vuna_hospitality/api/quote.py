"""Quote endpoints for the booking desk and reservations screens."""

import frappe
from frappe import _

from frappoint.vuna_hospitality.services import quote as quote_service
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.property_scope import assert_property_access


def _check_access(property_name: str) -> None:
	assert_property_access(property_name)
	if not frappe.has_permission("Rate Plan", "read"):
		raise frappe.PermissionError(_("You are not allowed to see room rates."))


@frappe.whitelist()
@require_hospitality
def get_quote(
	property: str,
	arrival: str,
	departure: str,
	room_type: str,
	rate_plan: str,
	adults: int = 1,
	children: int = 0,
) -> dict:
	"""Price one room type on one rate plan. Nothing is held or stored."""
	_check_access(property)
	return quote_service.quote(property, arrival, departure, room_type, rate_plan, adults, children).as_dict()


@frappe.whitelist()
@require_hospitality
def search_availability(
	property: str,
	arrival: str,
	departure: str,
	adults: int = 1,
	children: int = 0,
	rate_plan: str | None = None,
	room_type: str | None = None,
) -> list[dict]:
	"""Quote every room type and rate plan for the stay; offered options first, cheapest first."""
	_check_access(property)
	return [
		result.as_dict()
		for result in quote_service.search(
			property, arrival, departure, adults, children, rate_plan, room_type
		)
	]
