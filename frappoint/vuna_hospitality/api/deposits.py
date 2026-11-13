"""Deposit endpoints (feature F12): take a stay's deposit at the desk and waive it.

Taking a deposit is a cashier payment, so it needs a cashier role and an open shift, like any
payment. Waiving needs a Front Desk Manager. Each command owns its request's transaction and runs
through `run_with_inventory_retry`.
"""

import frappe
from frappe import _

from frappoint.vuna_hospitality.constants import CASHIER_ROLES, FOLIO_MANAGER_ROLES
from frappoint.vuna_hospitality.services import deposits
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.inventory import run_with_inventory_retry
from frappoint.vuna_hospitality.services.property_scope import assert_property_access


def _check(deposit: str, roles=None) -> str:
	row = frappe.db.get_value(deposits.DEPOSIT, deposit, ["property", "stay_reservation"], as_dict=True)
	if not row:
		raise frappe.DoesNotExistError(_("Guest Deposit {0} does not exist.").format(deposit))
	if roles:
		frappe.only_for(roles)
	assert_property_access(row.property)
	frappe.has_permission(deposits.DEPOSIT, "read", throw=True)
	return row.stay_reservation


@frappe.whitelist()
@require_hospitality
def get_deposit(deposit: str) -> dict:
	stay = _check(deposit)
	return deposits.deposit_details(stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def take_deposit(
	deposit: str,
	amount: float | None = None,
	mode_of_payment: str | None = None,
	payment_gateway: str | None = None,
	phone: str | None = None,
	reference_no: str | None = None,
	request_id: str | None = None,
) -> dict:
	"""Take the deposit, or part of it. An M-Pesa deposit waits for the guest to pay on the phone.
	Send the same `request_id` on a retry so it is taken once."""
	stay = _check(deposit, CASHIER_ROLES)
	request_id = (request_id or "").strip() or frappe.generate_hash(length=16)
	payment = run_with_inventory_retry(
		lambda: deposits.take_deposit(
			deposit,
			amount,
			mode_of_payment=mode_of_payment,
			payment_gateway=payment_gateway,
			phone=phone,
			reference_no=reference_no,
			request_id=request_id,
		)
	)
	details = deposits.deposit_details(stay)
	details["payment"] = payment
	return details


@frappe.whitelist(methods=["POST"])
@require_hospitality
def waive_deposit(deposit: str, reason: str) -> dict:
	"""Let the stay check in without its deposit."""
	stay = _check(deposit, FOLIO_MANAGER_ROLES)
	run_with_inventory_retry(lambda: deposits.waive(deposit, reason))
	return deposits.deposit_details(stay)
