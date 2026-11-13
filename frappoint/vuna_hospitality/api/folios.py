"""Folio Workspace endpoints: see a stay's folios, post a charge by Item, reverse a line, and
(F11) open more folios, move charges between them, settle, and issue credit notes.

Reading needs read access to Guest Folio and the property. Posting, moving charges, and opening
folios are for front-desk roles and cashiers; reversing is for Front Desk Managers (design §23.1);
settling is for cashiers; billing a company on account and credit notes are for managers and the
Hotel Accountant; rebuilding cached balances is for managers and the Hotel Accountant. Each command owns its request's transaction and runs through
`run_with_inventory_retry`, so a lock conflict with another request is retried, not shown.
"""

import frappe
from frappe import _

from frappoint.vuna_hospitality.constants import (
	CASHIER_ROLES,
	FOLIO_ACCOUNTING_ROLES,
	FOLIO_MANAGER_ROLES,
	FOLIO_POSTING_ROLES,
	FOLIO_REBUILD_ROLES,
	SETTLEMENT_ROLES,
)
from frappoint.vuna_hospitality.services import cashiering, folio, settlement
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.inventory import run_with_inventory_retry
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
		"can_settle": bool(roles & set(SETTLEMENT_ROLES)),
		"can_bill_company": bool(roles & set(FOLIO_ACCOUNTING_ROLES)),
		"can_credit": bool(roles & set(FOLIO_ACCOUNTING_ROLES)),
	}


def _invoice_preview(entry: dict) -> dict | None:
	"""What settling would invoice, for a folio that isn't invoiced yet."""
	row = entry["folio"]
	if row.get("sales_invoice") or row["status"] not in settlement.SETTLEABLE_STATUSES:
		return None
	try:
		return settlement.preview(row["name"])
	except settlement.SettlementError as error:
		frappe.clear_last_message()
		return {"error": str(error)}


@frappe.whitelist()
@require_hospitality
def get_stay_folios(stay: str) -> dict:
	"""The Folio Workspace for one stay: its folios, lines, pending nights and totals."""
	_check(STAY, stay)
	details = folio.stay_folio_details(stay)
	details["actions"] = _actions()
	# Payments (F10): each folio's payments and refunds, the user's shift, and the tenders.
	for entry in details["folios"]:
		entry["payments"] = cashiering.folio_payments(entry["folio"]["name"])
		entry["invoice"] = _invoice_preview(entry)
	property_name = details["stay"]["property"]
	can_take = bool(set(frappe.get_roles()) & set(CASHIER_ROLES))
	details["actions"]["can_take_payment"] = can_take
	details["cashier_shift"] = cashiering.current_shift(property_name) if can_take else None
	details["payment_options"] = cashiering.payment_options(property_name) if can_take else None
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
	# One key for every attempt, so a retry after a lock conflict can't post twice.
	request_id = (request_id or "").strip() or frappe.generate_hash(length=16)
	result = run_with_inventory_retry(
		lambda: folio.post_manual_charge(
			folio_name,
			item,
			quantity=quantity,
			rate=rate,
			description=description,
			stay_guest=stay_guest,
			notes=notes,
			request_id=request_id,
		)
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
	result = run_with_inventory_retry(lambda: folio.reverse_transaction(transaction, reason, notes=notes))
	details = _workspace(folio_name)
	details["posted"] = result
	return details


@frappe.whitelist(methods=["POST"])
@require_hospitality
def rebuild_folio_balance(folio_name: str) -> dict:
	"""Recompute a folio's cached totals from its transactions and report any drift."""
	_check(folio.FOLIO, folio_name, roles=FOLIO_REBUILD_ROLES)
	return run_with_inventory_retry(lambda: folio.rebuild_folio_balance(folio_name))


# --------------------------------------------------------------------------- F11


@frappe.whitelist(methods=["POST"])
@require_hospitality
def add_folio(
	stay: str,
	label: str | None = None,
	payee_customer: str | None = None,
	payee_guest_profile: str | None = None,
) -> dict:
	"""Open another folio on the stay, for a company, a companion, or the guest's extras."""
	_check(STAY, stay, "write", roles=FOLIO_POSTING_ROLES)
	name = run_with_inventory_retry(
		lambda: settlement.add_folio(stay, label, payee_customer, payee_guest_profile)
	)
	details = get_stay_folios(stay)
	details["added"] = name
	return details


@frappe.whitelist(methods=["POST"])
@require_hospitality
def set_folio_payee(
	folio_name: str, payee_customer: str | None = None, payee_guest_profile: str | None = None
) -> dict:
	_check(folio.FOLIO, folio_name, "write", roles=FOLIO_POSTING_ROLES)
	run_with_inventory_retry(lambda: settlement.set_payee(folio_name, payee_customer, payee_guest_profile))
	return _workspace(folio_name)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def transfer_charge(
	transaction: str,
	to_folio: str,
	amount: float | None = None,
	reason: str | None = None,
	request_id: str | None = None,
) -> dict:
	"""Move a charge, or `amount` of it, to another folio. Send the same `request_id` on a retry."""
	folio_name = frappe.db.get_value(folio.TRANSACTION, transaction, "guest_folio")
	if not folio_name:
		raise frappe.DoesNotExistError(_("Folio Transaction {0} does not exist.").format(transaction))
	_check(folio.FOLIO, folio_name, "write", roles=FOLIO_POSTING_ROLES)
	_check(folio.FOLIO, to_folio, "write")
	request_id = (request_id or "").strip() or frappe.generate_hash(length=16)
	result = run_with_inventory_retry(
		lambda: settlement.transfer(
			transaction, to_folio, amount or None, reason=reason, request_id=request_id
		)
	)
	details = _workspace(folio_name)
	details["moved"] = result
	return details


@frappe.whitelist(methods=["POST"])
@require_hospitality
def settle_folio(folio_name: str, transfer_to_ar: int = 0, override_reason: str | None = None) -> dict:
	"""Invoice the folio. With `transfer_to_ar`, the balance stays on the company's invoice.

	A rejected invoice isn't an error here: the folio is left Settlement Pending and the response
	carries the reason, so the cashier sees it after the page reloads.
	"""
	roles = FOLIO_ACCOUNTING_ROLES if frappe.utils.cint(transfer_to_ar) else SETTLEMENT_ROLES
	_check(folio.FOLIO, folio_name, "write", roles=roles)
	result = run_with_inventory_retry(
		lambda: settlement.settle(
			folio_name,
			transfer_to_ar=bool(frappe.utils.cint(transfer_to_ar)),
			override_reason=override_reason,
		)
	)
	details = _workspace(folio_name)
	details["settled"] = result
	return details


@frappe.whitelist(methods=["POST"])
@require_hospitality
def release_settlement(folio_name: str, reason: str) -> dict:
	"""Reopen a folio whose invoice was rejected, to correct it."""
	_check(folio.FOLIO, folio_name, "write", roles=SETTLEMENT_ROLES)
	run_with_inventory_retry(lambda: settlement.release_settlement(folio_name, reason))
	return _workspace(folio_name)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def issue_credit_note(transaction: str, reason: str) -> dict:
	"""Credit an invoiced charge: a reversal on the folio and a credit note in ERPNext."""
	folio_name = frappe.db.get_value(folio.TRANSACTION, transaction, "guest_folio")
	if not folio_name:
		raise frappe.DoesNotExistError(_("Folio Transaction {0} does not exist.").format(transaction))
	_check(folio.FOLIO, folio_name, "write", roles=FOLIO_ACCOUNTING_ROLES)
	result = run_with_inventory_retry(lambda: settlement.credit_note(transaction, reason))
	details = _workspace(folio_name)
	details["credited"] = result
	return details
