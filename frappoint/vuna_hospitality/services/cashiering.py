"""Payments and cashier shifts (design §16.1-16.3; feature F10).

**Cashier Shift.** A cashier opens a shift with a float before taking money. Closing is blind:
the cashier declares what they counted per Mode of Payment before seeing what the system
expected (float plus payments less refunds). Every variance needs a reason. A supervisor then
reviews the shift, and any variance posts to the property's cash over/short account through a
Journal Entry.

**Folio Payment.** One payment from one payer, split across one or more folios. A tender with a
Mode of Payment (cash, a card terminal, a bank transfer) is received at once. An M-Pesa payment
sends an STK push through the payments app and stays Pending until its callback, which calls
`on_payment_authorized` on the Folio Payment; a repeated callback changes nothing.

**Receiving** creates one ERPNext Payment Entry (Receive) against the payer as an unallocated
advance, then one Folio Payment Allocation and one credit Folio Transaction per folio, each with
the key `pay:<payment entry>:<folio>`. At settlement (F11) the advance is reconciled against the
folio's Sales Invoice. A refund is a Payment Entry (Pay) that references the original payment,
with a debit line on each folio, keyed `refund:<payment entry>:<folio>`.
"""

import frappe
from erpnext.accounts.party import get_party_account
from frappe import _
from frappe.utils import flt, getdate, now_datetime, nowdate

from frappoint.vuna_hospitality.services import folio
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.money import from_minor, to_minor
from frappoint.vuna_hospitality.services.reservations import _lock_row, _row
from frappoint.vuna_hospitality.services.status_commands import transition

SHIFT = "Cashier Shift"
PAYMENT = "Folio Payment"
ALLOCATION = "Folio Payment Allocation"

OPEN, CLOSED, REVIEWED = "Open", "Closed", "Reviewed"
PENDING, RECEIVED, FAILED, CANCELLED = "Pending", "Received", "Failed", "Cancelled"
RECEIVE, REFUND = "Receive", "Refund"
CREDIT, DEBIT = "Credit", "Debit"

# Set on records created by this service; the DocTypes refuse inserts without it.
SERVICE_FLAG = "from_cashiering"


class CashieringError(frappe.ValidationError):
	"""A payment, refund, or shift action isn't allowed in the current state."""


class NoOpenShiftError(CashieringError):
	"""Payments and refunds need the cashier's open shift."""


def _new(doctype: str, values: dict):
	doc = frappe.get_doc({"doctype": doctype, **values})
	doc.flags[SERVICE_FLAG] = True
	return doc.insert(ignore_permissions=True)


# --------------------------------------------------------------------------- shifts


def open_shift(property_name: str, opening_float=0, workstation: str | None = None) -> str:
	"""Open the user's shift at the property. A user has at most one open shift per property."""
	_lock_row("Hotel Property", property_name)
	existing = current_shift(property_name)
	if existing:
		frappe.throw(_("You already have an open shift: {0}.").format(existing), CashieringError)
	if flt(opening_float) < 0:
		frappe.throw(_("The opening float can't be negative."), CashieringError)
	prop = _row("Hotel Property", property_name, ["business_date", "currency", "company"])
	shift = _new(
		SHIFT,
		{
			"property": property_name,
			"cashier": frappe.session.user,
			"workstation": (workstation or "").strip() or None,
			"status": OPEN,
			"business_date": prop.business_date,
			"opened_at": now_datetime(),
			"currency": prop.currency,
			"opening_float": flt(opening_float),
			"float_mode_of_payment": cash_mode_of_payment(prop.company),
		},
	)
	log_event(SHIFT, shift.name, "Shift Opened", to_status=OPEN, data={"opening_float": flt(opening_float)})
	return shift.name


def current_shift(property_name: str, user: str | None = None) -> str | None:
	return frappe.db.get_value(
		SHIFT, {"property": property_name, "cashier": user or frappe.session.user, "status": OPEN}, "name"
	)


def require_shift(property_name: str) -> str:
	shift = current_shift(property_name)
	if not shift:
		frappe.throw(_("Open a cashier shift before taking or refunding money."), NoOpenShiftError)
	return shift


def cash_mode_of_payment(company: str) -> str | None:
	"""The enabled Mode of Payment of type Cash with an account in `company`."""
	modes = frappe.get_all(
		"Mode of Payment", filters={"type": "Cash", "enabled": 1}, pluck="name", order_by="name"
	)
	for mode in modes:
		if mode_account(mode, company, required=False):
			return mode
	return None


def mode_account(mode_of_payment: str, company: str, required: bool = True) -> str | None:
	account = frappe.db.get_value(
		"Mode of Payment Account", {"parent": mode_of_payment, "company": company}, "default_account"
	)
	if not account and required:
		frappe.throw(
			_("Set the {0} account for Mode of Payment {1}.").format(company, mode_of_payment),
			CashieringError,
		)
	return account


def expected_totals(shift_name: str) -> dict[str, int]:
	"""What the drawer should hold per Mode of Payment, in minor units: the float plus payments
	received in the shift, less refunds paid out in it."""
	shift = _row(SHIFT, shift_name, ["currency", "opening_float", "float_mode_of_payment"])
	totals: dict[str, int] = {}
	if shift.float_mode_of_payment:
		totals[shift.float_mode_of_payment] = to_minor(shift.opening_float, shift.currency)
	for row in frappe.get_all(
		PAYMENT,
		filters={"cashier_shift": shift_name, "status": RECEIVED},
		fields=["mode_of_payment", "payment_type", "amount"],
	):
		sign = 1 if row.payment_type == RECEIVE else -1
		totals[row.mode_of_payment] = totals.get(row.mode_of_payment, 0) + sign * to_minor(
			row.amount, shift.currency
		)
	return totals


def close_shift(shift_name: str, declared: dict, reasons: dict | None = None) -> dict:
	"""Close the shift with the cashier's counts. Expected totals are revealed only after this.

	`declared` maps Mode of Payment to the counted amount; a mode left out counts as zero. Each
	variance needs a reason in `reasons`.
	"""
	_lock_row(SHIFT, shift_name)
	shift = frappe.get_doc(SHIFT, shift_name)
	if shift.cashier != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only {0} can close their shift.").format(shift.cashier), frappe.PermissionError)
	if shift.status != OPEN:
		frappe.throw(_("Shift {0} is already {1}.").format(shift.name, _(shift.status)), CashieringError)
	if frappe.db.exists(PAYMENT, {"cashier_shift": shift.name, "status": PENDING}):
		frappe.throw(
			_("Wait for, or cancel, the pending phone payments of shift {0} first.").format(shift.name),
			CashieringError,
		)
	reasons = reasons or {}
	expected = expected_totals(shift.name)
	modes = sorted(set(expected) | {mode for mode in declared if mode})
	counts, missing = [], []
	for mode in modes:
		declared_minor = to_minor(declared.get(mode) or 0, shift.currency)
		variance = declared_minor - expected.get(mode, 0)
		reason = (reasons.get(mode) or "").strip()
		if variance and not reason:
			missing.append(mode)
		counts.append(
			{
				"mode_of_payment": mode,
				"declared": from_minor(declared_minor, shift.currency),
				"expected": from_minor(expected.get(mode, 0), shift.currency),
				"variance": from_minor(variance, shift.currency),
				"variance_reason": reason or None,
			}
		)
	if missing:
		frappe.throw(
			_("Your count differs from the system for {0}. Give a reason for each difference.").format(
				", ".join(missing)
			),
			CashieringError,
		)
	shift.set("counts", counts)
	transition(
		shift,
		CLOSED,
		updates={"closed_at": now_datetime()},
		event_type="Shift Closed",
		ignore_permissions=True,
	)
	return shift_summary(shift.name)


def review_shift(shift_name: str, notes: str | None = None, handover_to: str | None = None) -> dict:
	"""A supervisor accepts a closed shift. Variances post to cash over/short in a Journal Entry."""
	_lock_row(SHIFT, shift_name)
	shift = frappe.get_doc(SHIFT, shift_name)
	if shift.status != CLOSED:
		frappe.throw(
			_("Shift {0} is {1}; only a closed shift can be reviewed.").format(shift.name, _(shift.status))
		)
	if shift.cashier == frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Another supervisor must review your shift."), frappe.PermissionError)
	journal_entry = _post_variances(shift)
	transition(
		shift,
		REVIEWED,
		updates={
			"reviewed_by": frappe.session.user,
			"reviewed_at": now_datetime(),
			"review_notes": notes,
			"handover_to": handover_to,
			"journal_entry": journal_entry,
		},
		event_type="Shift Reviewed",
		ignore_permissions=True,
	)
	return shift_summary(shift.name)


def _post_variances(shift) -> str | None:
	lines = [row for row in shift.counts if to_minor(row.variance, shift.currency)]
	if not lines:
		return None
	prop = _row(
		"Hotel Property", shift.property, ["company", "cash_over_short_account", "default_cost_center"]
	)
	if not prop.cash_over_short_account:
		frappe.throw(
			_("Set the Cash Over/Short Account on Hotel Property {0} to post the shift's variances.").format(
				shift.property
			),
			CashieringError,
		)
	accounts = []
	for row in lines:
		account = mode_account(row.mode_of_payment, prop.company)
		amount = abs(flt(row.variance))
		over = flt(row.variance) > 0
		# Over: more money than expected, so the drawer's account gains it. Short: it lost it.
		accounts.append(
			{
				"account": account,
				"debit_in_account_currency": amount if over else 0,
				"credit_in_account_currency": 0 if over else amount,
				"cost_center": prop.default_cost_center,
			}
		)
		accounts.append(
			{
				"account": prop.cash_over_short_account,
				"debit_in_account_currency": 0 if over else amount,
				"credit_in_account_currency": amount if over else 0,
				"cost_center": prop.default_cost_center,
				"user_remark": f"{row.mode_of_payment}: {row.variance_reason}",
			}
		)
	journal = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"company": prop.company,
			"posting_date": getdate(shift.business_date) if shift.business_date else nowdate(),
			"user_remark": _("Cash over/short for cashier shift {0}").format(shift.name),
			"accounts": accounts,
		}
	)
	journal.insert(ignore_permissions=True)
	journal.submit()
	return journal.name


# --------------------------------------------------------------------------- payments


def payment_charge_code(mode_of_payment: str) -> str:
	code = frappe.db.get_value(
		"Charge Code",
		{"transaction_type": "Payment", "mode_of_payment": mode_of_payment, "is_active": 1},
		"name",
	)
	if not code:
		frappe.throw(
			_("No active Payment charge code uses Mode of Payment {0}. Ask a manager to add one.").format(
				mode_of_payment
			),
			CashieringError,
		)
	return code


def gateway_mode_of_payment(payment_gateway: str, currency: str) -> str:
	from frappoint.payments import _resolve_mode_of_payment_for_gateway

	mode = _resolve_mode_of_payment_for_gateway(payment_gateway, currency=currency)
	if not mode:
		frappe.throw(
			_("Payment Gateway {0} has no Mode of Payment.").format(payment_gateway), CashieringError
		)
	return mode


def payer_for(folio_name: str) -> str:
	"""The Customer who pays a folio: its payee, else a Customer made for its payee guest (D-3),
	else the property's walk-in Customer."""
	row = _row(folio.FOLIO, folio_name, ["payee_customer", "payee_guest_profile", "property"])
	if row.payee_customer:
		return row.payee_customer
	if row.payee_guest_profile:
		from frappoint.vuna_hospitality.services.guests import link_customer

		# The system creates the payer for the guest; the cashier needn't manage Customers.
		customer = link_customer(row.payee_guest_profile, ignore_permissions=True)
		frappe.db.set_value(folio.FOLIO, folio_name, "payee_customer", customer, update_modified=False)
		return customer
	walk_in = frappe.db.get_value("Hotel Property", row.property, "walk_in_customer")
	if not walk_in:
		frappe.throw(
			_("Folio {0} has no payee to take the payment from.").format(folio_name), CashieringError
		)
	return walk_in


def take_payment(
	property_name: str,
	splits: list[dict],
	*,
	mode_of_payment: str | None = None,
	payment_gateway: str | None = None,
	phone: str | None = None,
	reference_no: str | None = None,
	payer_customer: str | None = None,
	request_id: str | None = None,
) -> str:
	"""Take one payment for one or more folios. Returns the Folio Payment.

	`splits` is a list of {"folio", "amount"}. With a Mode of Payment the payment is received at
	once. With a phone `payment_gateway` (M-Pesa) an STK push is sent and the payment waits for its
	callback. The same `request_id` always returns the same payment.
	"""
	request_id = (request_id or "").strip() or None
	if request_id:
		existing = frappe.db.get_value(PAYMENT, {"request_id": request_id}, "name")
		if existing:
			return existing
	shift = require_shift(property_name)
	currency = frappe.db.get_value("Hotel Property", property_name, "currency")
	rows = _validated_splits(property_name, splits, currency)
	if payment_gateway:
		mode_of_payment = gateway_mode_of_payment(payment_gateway, currency)
		if not (phone or "").strip():
			frappe.throw(_("Enter the phone number to send the payment request to."), CashieringError)
	if not mode_of_payment:
		frappe.throw(_("Choose how the guest pays."), CashieringError)
	payment_charge_code(mode_of_payment)
	payer = payer_customer or payer_for(rows[0]["guest_folio"])
	total_minor = sum(to_minor(row["amount"], currency) for row in rows)

	payment = _new(
		PAYMENT,
		{
			"property": property_name,
			"payment_type": RECEIVE,
			"status": PENDING,
			"payer_customer": payer,
			"payer_name": frappe.db.get_value("Customer", payer, "customer_name"),
			"cashier_shift": shift,
			"request_id": request_id,
			"mode_of_payment": mode_of_payment,
			"payment_gateway": payment_gateway,
			"phone": (phone or "").strip() or None,
			"amount": from_minor(total_minor, currency),
			"currency": currency,
			"reference_no": (reference_no or "").strip() or None,
			"splits": rows,
		},
	)
	log_event(PAYMENT, payment.name, "Payment Requested", to_status=PENDING, data={"splits": rows})
	if payment_gateway:
		_request_phone_payment(payment)
	else:
		receive(payment.name)
	return payment.name


def _validated_splits(property_name: str, splits, currency: str) -> list[dict]:
	if isinstance(splits, str):
		splits = frappe.parse_json(splits)
	rows, seen = [], set()
	for split in splits or []:
		folio_name, amount_minor = (
			split.get("folio") or split.get("guest_folio"),
			to_minor(split.get("amount"), currency),
		)
		if amount_minor <= 0:
			continue
		row = _row(folio.FOLIO, folio_name, ["property", "status"])
		if not row or row.property != property_name:
			frappe.throw(_("Folio {0} is not part of this property.").format(folio_name), CashieringError)
		if row.status not in folio.POSTABLE_STATUSES:
			frappe.throw(
				_("Folio {0} is {1} and can't take a payment.").format(folio_name, _(row.status)),
				CashieringError,
			)
		if folio_name in seen:
			frappe.throw(_("Folio {0} is listed twice.").format(folio_name), CashieringError)
		seen.add(folio_name)
		rows.append({"guest_folio": folio_name, "amount": from_minor(amount_minor, currency)})
	if not rows:
		frappe.throw(_("Enter an amount for at least one folio."), CashieringError)
	return rows


def _request_phone_payment(payment) -> None:
	from payments.utils import get_payment_gateway_controller

	controller = get_payment_gateway_controller(payment.payment_gateway)
	controller.validate_transaction_currency(payment.currency)
	controller.request_for_payment(
		reference_doctype=PAYMENT,
		reference_docname=payment.name,
		payment_reference=payment.name,
		request_amount=payment.amount,
		sender=payment.phone,
		phone_number=payment.phone,
		currency=payment.currency,
		payment_gateway=payment.payment_gateway,
	)


def receive(payment_name: str, reference_no: str | None = None) -> str:
	"""Receive a pending payment: one Payment Entry, then an allocation and a folio credit per folio.

	Safe to call again: a received payment is returned unchanged, and every record it creates has a
	unique key. This is what a repeated gateway callback reaches.
	"""
	_lock_row(PAYMENT, payment_name)
	payment = frappe.get_doc(PAYMENT, payment_name)
	if payment.status == RECEIVED:
		return payment.name
	if payment.status != PENDING:
		frappe.throw(
			_("Payment {0} is {1} and can't be received.").format(payment.name, _(payment.status)),
			CashieringError,
		)
	if reference_no and not payment.reference_no:
		payment.reference_no = reference_no
	if not payment.payment_entry:
		payment.payment_entry = _payment_entry(payment, "Receive")
	code = payment_charge_code(payment.mode_of_payment)
	for split in payment.splits:
		split.allocation = _allocate(
			payment, split, code, CREDIT, f"pay:{payment.payment_entry}:{split.guest_folio}"
		)
	transition(
		payment,
		RECEIVED,
		updates={"received_at": now_datetime()},
		data={"payment_entry": payment.payment_entry},
		event_type="Payment Received",
		ignore_permissions=True,
	)
	return payment.name


def _allocate(
	payment, split, code: str, direction: str, key: str, refund_of_allocation: str | None = None
) -> str:
	existing = frappe.db.get_value(ALLOCATION, {"posting_key": key}, "name")
	if existing:
		return existing
	result = folio.post(
		split.guest_folio,
		code,
		split.amount,
		posting_key=key,
		direction=direction,
		description=_("Refund: {0}").format(payment.mode_of_payment)
		if direction == DEBIT
		else payment.mode_of_payment,
		source_doctype="Payment Entry",
		source_name=payment.payment_entry,
		reason=payment.reason,
		refund=direction == DEBIT,
	)
	allocation = frappe.get_doc(
		{
			"doctype": ALLOCATION,
			"docstatus": 1,
			"property": payment.property,
			"folio_payment": payment.name,
			"payment_entry": payment.payment_entry,
			"guest_folio": split.guest_folio,
			"direction": direction,
			"amount": split.amount,
			"folio_transaction": result["name"],
			"cashier_shift": payment.cashier_shift,
			"refund_of_allocation": refund_of_allocation,
			"posting_key": key,
		}
	)
	allocation.flags[SERVICE_FLAG] = True
	allocation.insert(ignore_permissions=True)
	return allocation.name


def _payment_entry(payment, payment_type: str) -> str:
	company = frappe.db.get_value("Hotel Property", payment.property, "company")
	drawer = mode_account(payment.mode_of_payment, company)
	party_account = get_party_account("Customer", payment.payer_customer, company)
	receive = payment_type == "Receive"
	paid_from, paid_to = (party_account, drawer) if receive else (drawer, party_account)
	# Give each account's currency and type, so the Payment Entry doesn't look them up through
	# ERPNext's get_account_details, which needs Payment Entry access the cashier doesn't have.
	details = {
		account: frappe.get_cached_value("Account", account, ["account_currency", "account_type"])
		for account in (paid_from, paid_to)
	}
	entry = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": payment_type,
			"company": company,
			"posting_date": nowdate(),
			"mode_of_payment": payment.mode_of_payment,
			"party_type": "Customer",
			"party": payment.payer_customer,
			"paid_from": paid_from,
			"paid_from_account_currency": details[paid_from][0],
			"paid_from_account_type": details[paid_from][1],
			"paid_to": paid_to,
			"paid_to_account_currency": details[paid_to][0],
			"paid_to_account_type": details[paid_to][1],
			"paid_amount": payment.amount,
			"received_amount": payment.amount,
			"reference_no": payment.reference_no or payment.name,
			"reference_date": nowdate(),
			"cost_center": frappe.db.get_value("Hotel Property", payment.property, "default_cost_center"),
			"remarks": (_("Hotel payment {0}") if receive else _("Hotel refund {0}")).format(payment.name),
		}
	)
	entry.insert(ignore_permissions=True)
	entry.submit()
	return entry.name


def fail(payment_name: str, reason: str, status: str = FAILED) -> None:
	"""A pending phone payment that failed or that the cashier gave up on."""
	_lock_row(PAYMENT, payment_name)
	payment = frappe.get_doc(PAYMENT, payment_name)
	if payment.status != PENDING:
		frappe.throw(_("Payment {0} is {1}.").format(payment.name, _(payment.status)), CashieringError)
	transition(payment, status, reason=reason, updates={"reason": reason}, ignore_permissions=True)


# --------------------------------------------------------------------------- refunds


def refund(
	payment_name: str,
	amounts: dict[str, float],
	*,
	reason: str,
	mode_of_payment: str | None = None,
	reference_no: str | None = None,
) -> str:
	"""Pay money back from a received payment. `amounts` maps each folio to the amount refunded.

	The refund can't exceed what is still allocated to a folio. Returns the refund Folio Payment.
	"""
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for the refund."), CashieringError)
	_lock_row(PAYMENT, payment_name)
	original = frappe.get_doc(PAYMENT, payment_name)
	if original.payment_type != RECEIVE or original.status != RECEIVED:
		frappe.throw(_("Only a received payment can be refunded."), CashieringError)
	shift = require_shift(original.property)
	currency = original.currency
	if isinstance(amounts, str):
		amounts = frappe.parse_json(amounts)

	rows = []
	for split in original.splits:
		wanted = to_minor(amounts.get(split.guest_folio) or 0, currency)
		if wanted <= 0:
			continue
		left = to_minor(split.amount, currency) - _refunded_minor(split.allocation, currency)
		if wanted > left:
			frappe.throw(
				_("Folio {0} has {1} left to refund from this payment.").format(
					split.guest_folio, from_minor(left, currency)
				),
				CashieringError,
			)
		rows.append(
			{
				"guest_folio": split.guest_folio,
				"amount": from_minor(wanted, currency),
				"source": split.allocation,
			}
		)
	if not rows:
		frappe.throw(_("Enter an amount to refund."), CashieringError)

	mode = mode_of_payment or original.mode_of_payment
	code = payment_charge_code(mode)
	total = sum(to_minor(row["amount"], currency) for row in rows)
	payment = _new(
		PAYMENT,
		{
			"property": original.property,
			"payment_type": REFUND,
			"status": PENDING,
			"refund_of": original.name,
			"payer_customer": original.payer_customer,
			"payer_name": original.payer_name,
			"cashier_shift": shift,
			"mode_of_payment": mode,
			"amount": from_minor(total, currency),
			"currency": currency,
			"reference_no": (reference_no or "").strip() or None,
			"reason": reason,
			"splits": [{"guest_folio": row["guest_folio"], "amount": row["amount"]} for row in rows],
		},
	)
	payment.payment_entry = _payment_entry(payment, "Pay")
	for split, row in zip(payment.splits, rows, strict=True):
		split.allocation = _allocate(
			payment,
			split,
			code,
			DEBIT,
			f"refund:{payment.payment_entry}:{split.guest_folio}",
			refund_of_allocation=row["source"],
		)
	transition(
		payment,
		RECEIVED,
		reason=reason,
		updates={"received_at": now_datetime()},
		data={"payment_entry": payment.payment_entry, "refund_of": original.name},
		event_type="Refund Paid",
		ignore_permissions=True,
	)
	return payment.name


def _refunded_minor(allocation: str, currency: str) -> int:
	refunds = frappe.get_all(
		ALLOCATION, filters={"refund_of_allocation": allocation, "docstatus": 1}, pluck="amount"
	)
	return sum(to_minor(amount, currency) for amount in refunds)


# --------------------------------------------------------------------------- views


def shift_summary(shift_name: str, reveal: bool | None = None) -> dict:
	"""The shift with its payments. Expected totals stay hidden from an open shift (blind close)."""
	shift = frappe.get_doc(SHIFT, shift_name)
	summary = shift.as_dict(no_default_fields=True)
	summary["name"] = shift.name
	payments = frappe.get_all(
		PAYMENT,
		filters={"cashier_shift": shift.name},
		fields=[
			"name",
			"payment_type",
			"status",
			"payer_name",
			"mode_of_payment",
			"amount",
			"reference_no",
			"received_at",
			"creation",
			"refund_of",
		],
		order_by="creation desc",
	)
	summary["payments"] = payments
	summary["modes"] = sorted(
		{row.mode_of_payment for row in payments} | ({shift.float_mode_of_payment} - {None})
	)
	if reveal is None:
		reveal = shift.status != OPEN
	if not reveal:
		summary["counts"] = []
	return summary


def payment_options(property_name: str) -> dict:
	"""Tenders the cashier can pick: Modes of Payment with a payment charge code, and phone gateways."""
	company = frappe.db.get_value("Hotel Property", property_name, "company")
	modes = [
		mode
		for mode in frappe.get_all(
			"Charge Code",
			filters={"transaction_type": "Payment", "is_active": 1, "mode_of_payment": ["is", "set"]},
			pluck="mode_of_payment",
			order_by="mode_of_payment asc",
			distinct=True,
		)
		if mode_account(mode, company, required=False)
	]
	gateways = []
	if frappe.db.exists("DocType", "Mpesa Settings"):
		for name in frappe.get_all("Mpesa Settings", pluck="name"):
			gateway = f"Mpesa-{name}"
			if frappe.db.exists("Payment Gateway", gateway):
				gateways.append({"name": gateway, "label": _("M-Pesa ({0})").format(name)})
	return {"modes": modes, "phone_gateways": gateways}


def folio_payments(folio_name: str) -> list[dict]:
	"""Payments and refunds that touched a folio, with what is left to refund."""
	allocations = frappe.get_all(
		ALLOCATION,
		filters={"guest_folio": folio_name, "docstatus": 1},
		fields=["name", "folio_payment", "direction", "amount", "refund_of_allocation"],
		order_by="creation asc",
	)
	result = []
	for row in allocations:
		payment = _row(
			PAYMENT,
			row.folio_payment,
			["mode_of_payment", "payment_type", "reference_no", "payer_name", "currency"],
		)
		refunded = 0 if row.direction == DEBIT else _refunded_minor(row.name, payment.currency)
		result.append(
			{
				**row,
				**payment,
				"refundable": 0
				if row.direction == DEBIT
				else from_minor(to_minor(row.amount, payment.currency) - refunded, payment.currency),
			}
		)
	return result
