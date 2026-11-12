"""Cashier page and payment endpoints: shifts, taking payments, refunds, and shift review.

Front-desk roles and cashiers take payments in their own open shift. Supervisors (Front Desk
Manager, Hospitality Manager, Hotel Accountant) review closed shifts. Payment commands run through
`run_with_inventory_retry`, so a lock conflict with another posting is retried, not shown.
"""

import frappe
from frappe import _

from frappoint.vuna_hospitality.constants import CASHIER_ROLES, CASHIER_SUPERVISOR_ROLES
from frappoint.vuna_hospitality.services import cashiering
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.inventory import run_with_inventory_retry
from frappoint.vuna_hospitality.services.property_scope import assert_property_access


def _check_property(property_name: str, roles=CASHIER_ROLES) -> None:
	frappe.only_for(roles)
	assert_property_access(property_name)


def _property_of(doctype: str, name: str) -> str:
	property_name = frappe.db.get_value(doctype, name, "property")
	if not property_name:
		raise frappe.DoesNotExistError(_("{0} {1} does not exist.").format(_(doctype), name))
	return property_name


def _is_supervisor() -> bool:
	return bool(set(frappe.get_roles()) & set(CASHIER_SUPERVISOR_ROLES))


@frappe.whitelist()
@require_hospitality
def get_cashier(property: str) -> dict:
	"""The user's open shift (blind), tenders, and, for supervisors, closed shifts to review."""
	_check_property(property)
	shift = cashiering.current_shift(property)
	to_review = []
	if _is_supervisor():
		to_review = [
			cashiering.shift_summary(name)
			for name in frappe.get_all(
				cashiering.SHIFT,
				filters={"property": property, "status": cashiering.CLOSED},
				pluck="name",
				order_by="closed_at asc",
			)
		]
	return {
		"shift": cashiering.shift_summary(shift) if shift else None,
		"options": cashiering.payment_options(property),
		"to_review": to_review,
		"can_review": _is_supervisor(),
		"recent": frappe.get_all(
			cashiering.SHIFT,
			filters={"property": property, "cashier": frappe.session.user, "status": ["!=", cashiering.OPEN]},
			fields=["name", "status", "business_date", "opened_at", "closed_at"],
			order_by="opened_at desc",
			limit=5,
		),
	}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def open_shift(property: str, opening_float: float = 0, workstation: str | None = None) -> dict:
	_check_property(property)
	cashiering.open_shift(property, opening_float, workstation)
	return get_cashier(property)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def close_shift(shift: str, declared: str | dict, reasons: str | dict | None = None) -> dict:
	"""Close the shift blind: `declared` maps Mode of Payment to the counted amount."""
	property_name = _property_of(cashiering.SHIFT, shift)
	_check_property(property_name)
	declared = frappe.parse_json(declared) if isinstance(declared, str) else declared
	reasons = frappe.parse_json(reasons) if isinstance(reasons, str) else reasons
	closed = cashiering.close_shift(shift, declared or {}, reasons or {})
	# The counts are revealed now that the cashier has declared (blind close).
	return {**get_cashier(property_name), "closed": closed}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def review_shift(shift: str, notes: str | None = None, handover_to: str | None = None) -> dict:
	property_name = _property_of(cashiering.SHIFT, shift)
	_check_property(property_name, roles=CASHIER_SUPERVISOR_ROLES)
	cashiering.review_shift(shift, notes, handover_to)
	return get_cashier(property_name)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def take_payment(
	property: str,
	splits: str | list,
	mode_of_payment: str | None = None,
	payment_gateway: str | None = None,
	phone: str | None = None,
	reference_no: str | None = None,
	request_id: str | None = None,
) -> dict:
	"""Take a payment split across folios. Send the same `request_id` on a retry."""
	_check_property(property)
	request_id = (request_id or "").strip() or frappe.generate_hash(length=16)
	name = run_with_inventory_retry(
		lambda: cashiering.take_payment(
			property,
			splits,
			mode_of_payment=mode_of_payment,
			payment_gateway=payment_gateway,
			phone=phone,
			reference_no=reference_no,
			request_id=request_id,
		)
	)
	return get_payment(name)


@frappe.whitelist()
@require_hospitality
def get_payment(payment: str) -> dict:
	"""A payment's status, for the screen waiting on a phone payment."""
	_check_property(_property_of(cashiering.PAYMENT, payment))
	doc = frappe.get_doc(cashiering.PAYMENT, payment)
	return {
		"name": doc.name,
		"status": doc.status,
		"amount": doc.amount,
		"currency": doc.currency,
		"mode_of_payment": doc.mode_of_payment,
		"payment_entry": doc.payment_entry,
		"reason": doc.reason,
		"splits": [{"guest_folio": row.guest_folio, "amount": row.amount} for row in doc.splits],
	}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def cancel_payment(payment: str, reason: str) -> dict:
	"""Give up on a pending phone payment, for example when the guest declined the prompt."""
	_check_property(_property_of(cashiering.PAYMENT, payment))
	cashiering.fail(payment, (reason or "").strip(), status=cashiering.CANCELLED)
	return get_payment(payment)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def refund_payment(
	payment: str,
	amounts: str | dict,
	reason: str,
	mode_of_payment: str | None = None,
	reference_no: str | None = None,
) -> dict:
	"""Refund part or all of a received payment. `amounts` maps each folio to the amount."""
	_check_property(_property_of(cashiering.PAYMENT, payment))
	name = run_with_inventory_retry(
		lambda: cashiering.refund(
			payment, amounts, reason=reason, mode_of_payment=mode_of_payment, reference_no=reference_no
		)
	)
	return get_payment(name)
