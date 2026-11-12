"""Folio Workspace endpoints: see a stay's folios, post a charge by Item, reverse a line.

Reading needs read access to Guest Folio and the property. Posting is for front-desk roles and
cashiers; reversing is for Front Desk Managers (design §23.1); rebuilding cached balances is for
managers and the Hotel Accountant. Each command owns its request's transaction.
"""

import frappe
from frappe import _

from frappoint.vuna_hospitality.constants import (
	FOLIO_MANAGER_ROLES,
	FOLIO_POSTING_ROLES,
	FOLIO_REBUILD_ROLES,
)
from frappoint.vuna_hospitality.services import folio
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.property_scope import assert_property_access

STAY = "Stay Reservation"


def _check(doctype: str, name: str, permission: str = "read", roles=None) -> str:
	property_name = frappe.db.get_value(doctype, name, "property")
	if not property_name:
		raise frappe.DoesNotExistError(_("{0} {1} does not exist.").format(_(doctype), name))
	if roles:
		frappe.only_for(roles)
	assert_property_access(property_name)
	frappe.has_permission(folio.FOLIO, permission, throw=True)
	return property_name


def _stay_of_folio(folio_name: str) -> str | None:
	return frappe.db.get_value(folio.FOLIO, folio_name, "stay_reservation")


def _workspace(folio_name: str) -> dict:
	stay = _stay_of_folio(folio_name)
	return folio.stay_folio_details(stay) if stay else folio.folio_details(folio_name)


def _actions() -> dict:
	roles = set(frappe.get_roles())
	return {
		"can_post": bool(roles & set(FOLIO_POSTING_ROLES)),
		"can_reverse": bool(roles & set(FOLIO_MANAGER_ROLES)),
		"can_rebuild": bool(roles & set(FOLIO_REBUILD_ROLES)),
	}


@frappe.whitelist()
@require_hospitality
def get_stay_folios(stay: str) -> dict:
	"""The Folio Workspace for one stay: its folios, lines, pending nights and totals."""
	_check(STAY, stay)
	details = folio.stay_folio_details(stay)
	details["actions"] = _actions()
	return details


@frappe.whitelist()
@require_hospitality
def search_items(folio_name: str, text: str = "") -> list[dict]:
	"""Items staff can post to this folio: sales Items that a charge code covers."""
	_check(folio.FOLIO, folio_name, "write", roles=FOLIO_POSTING_ROLES)
	return folio.search_postable_items(text)


@frappe.whitelist()
@require_hospitality
def get_item_rate(folio_name: str, item: str) -> dict:
	"""The default rate for an Item on this folio, and the charge code it will post with."""
	property_name = _check(folio.FOLIO, folio_name)
	code = folio.resolve_charge_code(item)
	return {
		"rate": folio.get_item_rate(item, property_name),
		"charge_code": code.name,
		"description": frappe.db.get_value("Item", item, "item_name"),
	}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def post_charge(
	folio_name: str,
	item: str,
	quantity: float = 1,
	rate: float | None = None,
	description: str | None = None,
	stay_guest: str | None = None,
	notes: str | None = None,
	request_id: str | None = None,
) -> dict:
	"""Post a charge by Item. Send the same `request_id` on a retry so it posts once."""
	_check(folio.FOLIO, folio_name, "write", roles=FOLIO_POSTING_ROLES)
	result = folio.post_manual_charge(
		folio_name,
		item,
		quantity=quantity,
		rate=rate,
		description=description,
		stay_guest=stay_guest,
		notes=notes,
		request_id=request_id,
	)
	details = _workspace(folio_name)
	details["posted"] = result
	return details


@frappe.whitelist(methods=["POST"])
@require_hospitality
def reverse_transaction(transaction: str, reason: str, notes: str | None = None) -> dict:
	"""Reverse a posted line with a reason. Reversing it again returns the same reversal."""
	folio_name = frappe.db.get_value(folio.TRANSACTION, transaction, "guest_folio")
	if not folio_name:
		raise frappe.DoesNotExistError(_("Folio Transaction {0} does not exist.").format(transaction))
	_check(folio.FOLIO, folio_name, "write", roles=FOLIO_MANAGER_ROLES)
	result = folio.reverse_transaction(transaction, reason, notes=notes)
	details = _workspace(folio_name)
	details["posted"] = result
	return details


@frappe.whitelist(methods=["POST"])
@require_hospitality
def rebuild_folio_balance(folio_name: str) -> dict:
	"""Recompute a folio's cached totals from its transactions and report any drift."""
	_check(folio.FOLIO, folio_name, roles=FOLIO_REBUILD_ROLES)
	return folio.rebuild_folio_balance(folio_name)
