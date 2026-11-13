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
from frappoint.vuna_hospitality.services import (
	cashiering,
	deposits,
	folio,
	house_accounts,
	routing,
	settlement,
)
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
	row = frappe.db.get_value(folio.FOLIO, folio_name, ["stay_reservation", "house_account"], as_dict=True)
	if row and row.stay_reservation:
		return folio.stay_folio_details(row.stay_reservation)
	if row and row.house_account:
		return house_accounts.account_folio_details(row.house_account)
	return folio.folio_details(folio_name)


def _add_cashiering(details: dict, property_name: str) -> dict:
	"""Payments (F10) and the invoice preview (F11) for each folio of a workspace."""
	details["actions"] = _actions()
	for entry in details["folios"]:
		entry["payments"] = cashiering.folio_payments(entry["folio"]["name"])
		entry["invoice"] = _invoice_preview(entry)
	can_take = bool(set(frappe.get_roles()) & set(CASHIER_ROLES))
	details["actions"]["can_take_payment"] = can_take
	details["cashier_shift"] = cashiering.current_shift(property_name) if can_take else None
	details["payment_options"] = cashiering.payment_options(property_name) if can_take else None
	return details


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
	details = _add_cashiering(folio.stay_folio_details(stay), frappe.db.get_value(STAY, stay, "property"))
	# F12: the stay's routing rules and deposit, and whether late charges are open.
	details["routing_rules"] = routing.stay_rules(stay)
	details["deposit"] = deposits.deposit_details(stay)
	details["actions"]["can_route"] = details["actions"]["can_post"]
	details["actions"]["can_waive_deposit"] = details["actions"]["can_reverse"]
	details["actions"]["can_add_folio"] = details["stay"][
		"status"
	] not in settlement.CLOSED_STAY_STATUSES and (
		details["stay"]["status"] != "Checked Out" or details["actions"]["can_reverse"]
	)
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
	reason: str | None = None,
) -> dict:
	"""Post a charge by Item. Send the same `request_id` on a retry so it posts once. A late charge
	after check-out needs a Front Desk Manager and a `reason` (F12)."""
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
			reason=reason,
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


# --------------------------------------------------------------------------- F12 routing


@frappe.whitelist(methods=["POST"])
@require_hospitality
def add_routing_rule(
	stay: str,
	target_folio: str,
	route: str,
	charge_code: str | None = None,
	item_group: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Send the stay's automatic charges (night audit, fees) of one kind to one of its folios."""
	_check(STAY, stay, "write", roles=FOLIO_POSTING_ROLES)
	run_with_inventory_retry(
		lambda: routing.add_rule(
			stay, target_folio, route, charge_code=charge_code, item_group=item_group, notes=notes
		)
	)
	return get_stay_folios(stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def remove_routing_rule(rule: str, reason: str) -> dict:
	stay = frappe.db.get_value(routing.RULE, rule, "stay_reservation")
	if not stay:
		raise frappe.DoesNotExistError(_("Charge Routing Rule {0} does not exist.").format(rule))
	_check(STAY, stay, "write", roles=FOLIO_POSTING_ROLES)
	run_with_inventory_retry(lambda: routing.remove_rule(rule, reason))
	return get_stay_folios(stay)


# --------------------------------------------------------------------------- F12 house accounts

HOUSE_ACCOUNT_ROLES = (*FOLIO_ACCOUNTING_ROLES,)


def _check_account(account: str, roles=None) -> str:
	property_name = frappe.db.get_value(house_accounts.ACCOUNT, account, "property")
	if not property_name:
		raise frappe.DoesNotExistError(_("House Account {0} does not exist.").format(account))
	if roles:
		frappe.only_for(roles)
	assert_property_access(property_name)
	frappe.has_permission(house_accounts.ACCOUNT, "read", throw=True)
	return property_name


@frappe.whitelist()
@require_hospitality
def get_house_accounts(property: str) -> dict:
	assert_property_access(property)
	frappe.has_permission(house_accounts.ACCOUNT, "read", throw=True)
	return {
		"accounts": house_accounts.account_list(property),
		"can_manage": bool(set(frappe.get_roles()) & set(HOUSE_ACCOUNT_ROLES)),
	}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def create_house_account(
	property: str,
	account_name: str,
	account_type: str = "Permanent",
	payee_customer: str | None = None,
	valid_from: str | None = None,
	valid_to: str | None = None,
	notes: str | None = None,
) -> dict:
	frappe.only_for(HOUSE_ACCOUNT_ROLES)
	assert_property_access(property)
	name = run_with_inventory_retry(
		lambda: house_accounts.create(
			property,
			account_name,
			account_type=account_type,
			payee_customer=payee_customer,
			valid_from=valid_from,
			valid_to=valid_to,
			notes=notes,
		)
	)
	return {"name": name, **get_house_accounts(property)}


@frappe.whitelist()
@require_hospitality
def get_house_account_folios(account: str) -> dict:
	"""The Folio Workspace for a House Account: its current folio and the last settled ones."""
	property_name = _check_account(account)
	frappe.has_permission(folio.FOLIO, "read", throw=True)
	details = _add_cashiering(house_accounts.account_folio_details(account), property_name)
	details["routing_rules"] = []
	details["deposit"] = None
	current = details["house_account"]["current_folio"]
	needs_folio = details["house_account"]["status"] == house_accounts.ACTIVE and (
		not current
		or frappe.db.get_value(folio.FOLIO, current, "status")
		not in (*folio.POSTABLE_STATUSES, settlement.SETTLEMENT_PENDING)
	)
	details["actions"].update(
		{
			"can_route": False,
			"can_waive_deposit": False,
			"can_add_folio": False,
			"can_open_house_folio": needs_folio and details["actions"]["can_post"],
		}
	)
	return details


@frappe.whitelist(methods=["POST"])
@require_hospitality
def open_house_account_folio(account: str) -> dict:
	"""Start the account's next folio after the last one was settled."""
	_check_account(account, FOLIO_POSTING_ROLES)
	run_with_inventory_retry(lambda: house_accounts.ensure_folio(account))
	return get_house_account_folios(account)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def close_house_account(account: str, reason: str) -> dict:
	property_name = _check_account(account, HOUSE_ACCOUNT_ROLES)
	run_with_inventory_retry(lambda: house_accounts.close(account, reason))
	return get_house_accounts(property_name)
