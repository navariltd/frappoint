"""Guest deposits through ERPNext (design §16.4; feature F12).

A **Guest Deposit** is only the link from a stay to the payments that paid its deposit, and the
policy that asked for it. The money is ERPNext's:

- **Request and receive.** The deposit is a cashier payment (F10) on the stay's default folio,
  marked with the deposit: cash and card at once, M-Pesa through the gateway's STK push and its
  callback. Each becomes an advance Payment Entry against the payee. With the Company's "Book
  Advance Payments in Separate Party Account", ERPNext posts it to the advance (liability)
  account; a deposit is never revenue.
- **Apply.** Settlement attaches the folio's Payment Entries to its Sales Invoice as advances
  (F11), so the deposit pays the invoice. The deposit is then Applied.
- **Forfeit.** Cancelling inside the penalty window, or not arriving, posts the policy fee on the
  same folio. The deposit pays the fee, only the excess is refunded (a Payment Entry, Pay), and the
  folio settles into the fee's invoice. The deposit is then Forfeited.
- **Release.** A deposit still unpaid when it falls due releases the stay, if the policy says so.

Received and refunded amounts are read from the Payment Entries every time; the deposit stores
only what the policy required.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate

from frappoint.vuna_hospitality.constants import FOLIO_MANAGER_ROLES
from frappoint.vuna_hospitality.services import folio
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.money import from_minor, to_minor
from frappoint.vuna_hospitality.services.reservations import STAY, _row
from frappoint.vuna_hospitality.services.status_commands import transition

DEPOSIT = "Guest Deposit"
PAYMENT = "Folio Payment"
SERVICE_FLAG = "from_deposit_service"

REQUESTED, PARTLY_PAID, RECEIVED = "Requested", "Partly Paid", "Received"
APPLIED, FORFEITED, REFUNDED, WAIVED, RELEASED = "Applied", "Forfeited", "Refunded", "Waived", "Released"
OPEN_STATUSES = (REQUESTED, PARTLY_PAID, RECEIVED)
# Stays a deposit can still be taken for.
PAYABLE_STAY_STATUSES = ("Confirmed", "Due In", "In House", "Due Out")
NO_DEPOSIT = "None"


class DepositError(frappe.ValidationError):
	pass


class DepositRequiredError(DepositError):
	"""Check-in refused: the stay's deposit isn't paid."""


# --------------------------------------------------------------------------- request


def create_for_stay(stay_name: str) -> str | None:
	"""Ask for the deposit the stay's policy requires, when it is confirmed. Safe to call again."""
	existing = frappe.db.get_value(DEPOSIT, {"stay_reservation": stay_name}, "name")
	if existing:
		return existing
	from frappoint.vuna_hospitality.services.policies import pending_nights, policy_amount

	stay = frappe.get_doc(STAY, stay_name)
	policy = (
		frappe._dict(frappe.parse_json(stay.deposit_policy_snapshot))
		if stay.deposit_policy_snapshot
		else None
	)
	if not policy or (policy.deposit_type or NO_DEPOSIT) == NO_DEPOSIT:
		return None
	required = policy_amount(
		policy.deposit_type, policy.deposit_value, pending_nights(stay.name), stay.currency
	)
	if required <= 0:
		return None
	folio_name = stay.default_folio or folio.ensure_default_folio(stay.name)
	business_date = getdate(frappe.db.get_value("Hotel Property", stay.property, "business_date"))
	due = add_days(business_date, policy.deposit_due_days_after_booking or 0)
	doc = frappe.get_doc(
		{
			"doctype": DEPOSIT,
			"property": stay.property,
			"hotel_booking": stay.hotel_booking,
			"stay_reservation": stay.name,
			"guest_folio": folio_name,
			"status": REQUESTED,
			"deposit_policy": policy.name,
			"payee_customer": frappe.db.get_value(folio.FOLIO, folio_name, "payee_customer"),
			"currency": stay.currency,
			"required_amount": from_minor(required, stay.currency),
			# Never due after arrival: check-in needs it.
			"due_date": min(getdate(due), getdate(stay.arrival_date)),
			"release_if_unpaid": policy.release_if_unpaid,
		}
	)
	doc.flags[SERVICE_FLAG] = True
	doc.insert(ignore_permissions=True)
	log_event(
		STAY,
		stay.name,
		"Deposit Requested",
		data={"deposit": doc.name, "amount": doc.required_amount, "due": str(doc.due_date)},
	)
	return doc.name


# --------------------------------------------------------------------------- amounts


def amounts(deposit_name: str) -> frappe._dict:
	"""What the deposit's Payment Entries received and paid back, in minor units."""
	currency = frappe.db.get_value(DEPOSIT, deposit_name, "currency")
	payments = frappe.get_all(
		PAYMENT,
		filters={"guest_deposit": deposit_name, "payment_type": "Receive", "status": "Received"},
		fields=["name", "payment_entry"],
	)
	refunds = frappe.get_all(
		PAYMENT,
		filters={
			"refund_of": ["in", [row.name for row in payments] or [""]],
			"payment_type": "Refund",
			"status": "Received",
		},
		pluck="payment_entry",
	)
	received = _entries_total([row.payment_entry for row in payments], currency)
	refunded = _entries_total(refunds, currency)
	return frappe._dict(
		currency=currency,
		payments=[row.name for row in payments],
		received=received,
		refunded=refunded,
		held=received - refunded,
	)


def _entries_total(entries: list[str], currency: str) -> int:
	if not entries:
		return 0
	paid = frappe.get_all(
		"Payment Entry", filters={"name": ["in", entries], "docstatus": 1}, pluck="paid_amount"
	)
	return sum(to_minor(amount, currency) for amount in paid)


def refresh(deposit_name: str) -> str:
	"""Move an open deposit to Requested, Partly Paid or Received from its payments."""
	doc = frappe.get_doc(DEPOSIT, deposit_name)
	if doc.status not in OPEN_STATUSES:
		return doc.status
	totals = amounts(doc.name)
	required = to_minor(doc.required_amount, doc.currency)
	status = RECEIVED if totals.held >= required else PARTLY_PAID if totals.held > 0 else REQUESTED
	if status != doc.status:
		transition(
			doc,
			status,
			data={"held": from_minor(totals.held, doc.currency)},
			event_type="Deposit Status Changed",
			ignore_permissions=True,
		)
	return status


def refresh_for_payment(payment_name: str) -> None:
	"""Called after a payment or refund is received, to update the deposit it belongs to."""
	row = _row(PAYMENT, payment_name, ["guest_deposit", "refund_of"])
	deposit = row.guest_deposit or (
		row.refund_of and frappe.db.get_value(PAYMENT, row.refund_of, "guest_deposit")
	)
	if deposit:
		refresh(deposit)


# --------------------------------------------------------------------------- take


def take_deposit(
	deposit_name: str,
	amount=None,
	*,
	mode_of_payment: str | None = None,
	payment_gateway: str | None = None,
	phone: str | None = None,
	reference_no: str | None = None,
	request_id: str | None = None,
) -> str:
	"""Take the deposit, or `amount` of it. Returns the Folio Payment (pending for M-Pesa)."""
	from frappoint.vuna_hospitality.services import cashiering

	doc = frappe.get_doc(DEPOSIT, deposit_name)
	if doc.status not in OPEN_STATUSES:
		frappe.throw(_("Deposit {0} is {1}.").format(doc.name, _(doc.status)), DepositError)
	stay_status = frappe.db.get_value(STAY, doc.stay_reservation, "status")
	if stay_status not in PAYABLE_STAY_STATUSES:
		frappe.throw(_("Stay {0} is {1}.").format(doc.stay_reservation, _(stay_status)), DepositError)
	left = to_minor(doc.required_amount, doc.currency) - amounts(doc.name).held
	wanted = to_minor(amount, doc.currency) if amount not in (None, "") else left
	if wanted <= 0:
		frappe.throw(_("Deposit {0} is already paid.").format(doc.name), DepositError)
	payment = cashiering.take_payment(
		doc.property,
		[{"folio": doc.guest_folio, "amount": from_minor(wanted, doc.currency)}],
		mode_of_payment=mode_of_payment,
		payment_gateway=payment_gateway,
		phone=phone,
		reference_no=reference_no,
		payer_customer=doc.payee_customer,
		request_id=request_id,
		guest_deposit=doc.name,
	)
	refresh(doc.name)
	return payment


def for_stay(stay_name: str) -> str | None:
	return frappe.db.get_value(DEPOSIT, {"stay_reservation": stay_name}, "name")


def assert_satisfied(stay) -> None:
	"""Check-in needs the stay's deposit paid, or waived by a Front Desk Manager."""
	deposit = for_stay(stay.name)
	if not deposit:
		return
	doc = frappe.get_doc(DEPOSIT, deposit)
	if doc.status not in OPEN_STATUSES:
		return
	totals = amounts(doc.name)
	short = to_minor(doc.required_amount, doc.currency) - totals.held
	if short > 0:
		frappe.throw(
			_(
				"Take the deposit before check-in: {0} of {1} is still to pay (deposit {2}). A Front Desk Manager can waive it."
			).format(
				frappe.format(
					from_minor(short, doc.currency), {"fieldtype": "Currency", "options": doc.currency}
				),
				frappe.format(doc.required_amount, {"fieldtype": "Currency", "options": doc.currency}),
				doc.name,
			),
			DepositRequiredError,
		)


def waive(deposit_name: str, reason: str) -> None:
	"""A Front Desk Manager lets the stay go ahead without (the rest of) its deposit."""
	if not set(FOLIO_MANAGER_ROLES) & set(frappe.get_roles()):
		frappe.throw(_("Only a Front Desk Manager can waive a deposit."), frappe.PermissionError)
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for waiving the deposit."), DepositError)
	doc = frappe.get_doc(DEPOSIT, deposit_name)
	if doc.status == WAIVED:
		return
	if doc.status not in OPEN_STATUSES:
		frappe.throw(_("Deposit {0} is {1}.").format(doc.name, _(doc.status)), DepositError)
	transition(
		doc,
		WAIVED,
		reason=reason,
		updates={"reason": reason},
		event_type="Deposit Waived",
		ignore_permissions=True,
	)


# --------------------------------------------------------------------------- forfeit and apply


def settle_after_fee(stay_name: str, reason: str) -> dict | None:
	"""After a cancellation or no-show: the deposit pays the fee and only the excess goes back.

	The excess is refunded through the user's open cashier shift. Without one, the folio keeps
	the credit for a cashier to refund, and this returns {"refund_waiting": amount}. Once nothing
	is owed either way, the folio is settled: one invoice for the fee, paid by the deposit.
	"""
	from frappoint.vuna_hospitality.services import cashiering, settlement

	deposit = for_stay(stay_name)
	if not deposit:
		return None
	doc = frappe.get_doc(DEPOSIT, deposit)
	if doc.status not in OPEN_STATUSES:
		return None
	if amounts(doc.name).held <= 0:
		# Nothing was paid: the stay no longer asks for it.
		transition(
			doc,
			RELEASED,
			reason=reason,
			updates={"reason": reason},
			event_type="Deposit Released",
			ignore_permissions=True,
		)
		return None
	row = folio.lock_folio(doc.guest_folio)
	if row.status not in settlement.SETTLEABLE_STATUSES:
		return None
	currency = row.currency
	balance = to_minor(row.balance, currency)
	result = {"deposit": doc.name, "folio": doc.guest_folio, "refunded": 0}
	if balance > 0:
		# The fee is more than the deposit: the guest owes the rest.
		result["owing"] = from_minor(balance, currency)
		return result
	if balance < 0:
		if not cashiering.current_shift(doc.property):
			result["refund_waiting"] = from_minor(-balance, currency)
			return result
		result["refunded"] = from_minor(_refund_excess(doc, -balance, reason), currency)
	result.update(settlement.settle(doc.guest_folio))
	return result


def _refund_excess(doc, excess: int, reason: str) -> int:
	"""Refund `excess` minor units from the deposit's payments, newest first."""
	from frappoint.vuna_hospitality.services import cashiering

	refunded = 0
	for payment in reversed(amounts(doc.name).payments):
		if refunded >= excess:
			break
		split = frappe.db.get_value(
			"Folio Payment Split",
			{"parent": payment, "parenttype": PAYMENT, "guest_folio": doc.guest_folio},
			["amount", "allocation"],
			as_dict=True,
		)
		if not split:
			continue
		left = to_minor(split.amount, doc.currency) - cashiering._refunded_minor(
			split.allocation, doc.currency
		)
		take = min(left, excess - refunded)
		if take <= 0:
			continue
		cashiering.refund(
			payment,
			{doc.guest_folio: from_minor(take, doc.currency)},
			reason=_("Deposit returned after the fee: {0}").format(reason),
		)
		refunded += take
	return refunded


def on_folio_settled(folio_name: str) -> None:
	"""The folio was invoiced: its open deposits were applied to the invoice (or to the fee)."""
	for name in frappe.get_all(
		DEPOSIT, filters={"guest_folio": folio_name, "status": ["in", list(OPEN_STATUSES)]}, pluck="name"
	):
		doc = frappe.get_doc(DEPOSIT, name)
		totals = amounts(name)
		stay_status = frappe.db.get_value(STAY, doc.stay_reservation, "status")
		if totals.held <= 0:
			status = REFUNDED
		elif stay_status in ("Cancelled", "No Show"):
			status = FORFEITED
		else:
			status = APPLIED
		transition(
			doc,
			status,
			data={
				"held": from_minor(totals.held, doc.currency),
				"refunded": from_minor(totals.refunded, doc.currency),
				"sales_invoice": frappe.db.get_value(folio.FOLIO, folio_name, "sales_invoice"),
			},
			event_type=f"Deposit {status}",
			ignore_permissions=True,
		)


# --------------------------------------------------------------------------- release


def overdue(property_name: str, business_date) -> list[str]:
	"""Deposits due by `business_date` that are still not fully paid and release their stay."""
	return frappe.get_all(
		DEPOSIT,
		filters={
			"property": property_name,
			"status": ["in", [REQUESTED, PARTLY_PAID]],
			"release_if_unpaid": 1,
			"due_date": ["<=", getdate(business_date)],
		},
		pluck="name",
		order_by="due_date asc, name asc",
	)


def release(deposit_name: str) -> bool:
	"""Cancel the stay of an unpaid deposit, without a fee. Returns False if nothing changed."""
	from frappoint.vuna_hospitality.services.reservations import CANCELLABLE_STAY_STATUSES, cancel

	doc = frappe.get_doc(DEPOSIT, deposit_name)
	if doc.status not in (REQUESTED, PARTLY_PAID):
		return False
	stay_status = frappe.db.get_value(STAY, doc.stay_reservation, "status")
	if stay_status not in CANCELLABLE_STAY_STATUSES:
		return False
	reason = _("Deposit not paid by {0}").format(frappe.format(doc.due_date, "Date"))
	# Cancelling releases a deposit with nothing paid. A part payment stays on the folio, as a
	# credit for the cashier to refund, and the deposit is released here.
	cancel(doc.stay_reservation, reason, charge_fee=False)
	doc.reload()
	if doc.status != RELEASED:
		transition(
			doc,
			RELEASED,
			reason=reason,
			updates={"reason": reason},
			event_type="Deposit Released",
			ignore_permissions=True,
		)
	return True


def reopen(stay_name: str) -> None:
	"""A reinstated stay asks for its released deposit again, due on the new business date."""
	deposit = for_stay(stay_name)
	if not deposit:
		return
	doc = frappe.get_doc(DEPOSIT, deposit)
	if doc.status not in (RELEASED, WAIVED):
		return
	business_date = getdate(frappe.db.get_value("Hotel Property", doc.property, "business_date"))
	transition(
		doc,
		REQUESTED,
		updates={"due_date": business_date, "reason": None},
		event_type="Deposit Requested",
		ignore_permissions=True,
	)
	refresh(doc.name)


# --------------------------------------------------------------------------- views


def deposit_details(stay_name: str) -> dict | None:
	deposit = for_stay(stay_name)
	if not deposit:
		return None
	doc = frappe.get_doc(DEPOSIT, deposit)
	totals = amounts(deposit)
	required = to_minor(doc.required_amount, doc.currency)
	return {
		"name": doc.name,
		"status": doc.status,
		"currency": doc.currency,
		"guest_folio": doc.guest_folio,
		"required_amount": doc.required_amount,
		"received": from_minor(totals.received, doc.currency),
		"refunded": from_minor(totals.refunded, doc.currency),
		"held": from_minor(totals.held, doc.currency),
		"outstanding": from_minor(max(required - totals.held, 0), doc.currency)
		if doc.status in OPEN_STATUSES
		else 0,
		"due_date": doc.due_date,
		"release_if_unpaid": doc.release_if_unpaid,
		"policy_name": frappe.db.get_value("Hotel Policy", doc.deposit_policy, "policy_name"),
		"reason": doc.reason,
		"payments": totals.payments,
	}
