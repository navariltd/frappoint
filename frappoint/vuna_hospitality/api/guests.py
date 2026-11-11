"""Guest profile endpoints for the booking screen and the desk form."""

import frappe
from frappe import _

from frappoint.vuna_hospitality.services import guests as guest_service
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality

GUEST_PROFILE = guest_service.GUEST_PROFILE


def _check(permission: str, guest_profile: str | None = None) -> None:
	allowed = (
		frappe.has_permission(GUEST_PROFILE, permission, doc=guest_profile)
		if guest_profile
		else frappe.has_permission(GUEST_PROFILE, permission)
	)
	if not allowed:
		raise frappe.PermissionError(_("You are not allowed to {0} guest profiles.").format(_(permission)))


@frappe.whitelist()
@require_hospitality
def search_guests(text: str, limit: int = guest_service.DEFAULT_SEARCH_LIMIT) -> list[dict]:
	"""Find guests by name, phone, or email."""
	_check("read")
	return guest_service.search_guests(text, limit)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def create_guest(
	first_name: str,
	last_name: str | None = None,
	email: str | None = None,
	mobile_no: str | None = None,
	is_provisional: bool = False,
	force: bool = False,
) -> dict:
	"""Create a guest, or return existing guests with the same email or phone (unless `force`)."""
	_check("create")
	return guest_service.create_guest(
		first_name,
		last_name,
		email,
		mobile_no,
		is_provisional=frappe.utils.sbool(is_provisional),
		force=frappe.utils.sbool(force),
	)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def link_customer(guest_profile: str, customer: str | None = None) -> str:
	"""Link a paying Customer to the guest, creating an individual Customer if none is given."""
	if not customer and not frappe.has_permission("Customer", "create"):
		raise frappe.PermissionError(_("You are not allowed to create Customers."))
	return guest_service.link_customer(guest_profile, customer)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def reveal_id_document(guest_profile: str) -> dict:
	"""Show the guest's full ID number. Each call is recorded in the event log."""
	return guest_service.reveal_id_document(guest_profile)


@frappe.whitelist()
@require_hospitality
def get_relationships(guest_profile: str, include_ended: bool = False) -> list[dict]:
	"""Everyone related to the guest, from either side of each relationship."""
	_check("read", guest_profile)
	return guest_service.get_relationships(guest_profile, include_ended=frappe.utils.sbool(include_ended))
