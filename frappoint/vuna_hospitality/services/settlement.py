"""Several folios per stay, transfers between them, and settlement into ERPNext (design §15.3,
§17.3-17.6; feature F11).

**Folios.** A stay has its default folio and may open more, up to the property's limit, each with
its own payee: the guest, a companion, or a company. A folio's payee can change until it takes a
payment, because the payment's ERPNext Payment Entry is made out to the payee.

**Transfers.** A charge, or part of one, moves to another folio of the same stay or booking as two
lines: a credit on the source folio and a debit on the target, both pointing at the line that
moved (`transfer_of`). The amount, its tax, and the tax per account are split in minor units, and
moving whatever is left moves exactly the rest, so nothing is lost to rounding.

**Settlement.** `settle()` turns a folio into one Sales Invoice for its payee, through ERPNext's
own insert and submit, so hooks of installed apps (a tax-compliance app, for example) run as usual:

1. Lines are grouped by charge-code print group and Item, so a company's invoice shows "Food and
   Beverage", not each drink. Reversals, transfers, and allowance offsets net out in their group.
2. Each line's tax was already computed by ERPNext when it was posted (services/taxes.py). The
   invoice carries those amounts as "Actual" tax rows per account, so it equals the folio to the
   minor unit; recomputing on grouped lines could differ by rounding.
3. The folio's payments are attached as the invoice's advances, in the same submission.
4. A paid folio closes. A company payee's balance can stay on the invoice instead, as an ERPNext
   receivable ("Transferred to AR"), within its credit limit unless ERPNext's Credit Controller
   overrides.

If submission is rejected, everything rolls back, the folio is left in Settlement Pending with the
error, and retrying creates no second invoice. A settled folio is corrected with a credit note
(a return Sales Invoice) and a reversal; Frappoint never cancels a submitted invoice.
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime, strip_html

from frappoint.vuna_hospitality.constants import FOLIO_ACCOUNTING_ROLES
from frappoint.vuna_hospitality.services import folio
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.money import from_minor, to_minor
from frappoint.vuna_hospitality.services.reservations import BOOKING, STAY, _row
from frappoint.vuna_hospitality.services.status_commands import transition

SETTLEMENT_PENDING = "Settlement Pending"
SETTLED = "Settled"
TRANSFERRED_TO_AR = "Transferred to AR"
SETTLEABLE_STATUSES = (*folio.POSTABLE_STATUSES, SETTLEMENT_PENDING)

# Stays that can't open another folio.
CLOSED_STAY_STATUSES = ("Cancelled", "Expired", "No Show")
# Lines that are money in, not something billed. They become the invoice's advances.
PAYMENT_TYPES = ("Payment", "Deposit")
EXTERNALLY_ACCOUNTED = "Externally Accounted"
SAVEPOINT = "folio_settlement"


class SettlementError(frappe.ValidationError):
	"""The folio can't be settled, transferred, or corrected as asked."""


class CreditLimitError(SettlementError):
	"""Transferring the balance would take the company over its ERPNext credit limit."""


# --------------------------------------------------------------------------- folios


def add_folio(
	stay_name: str,
	label: str | None = None,
	payee_customer: str | None = None,
	payee_guest_profile: str | None = None,
) -> str:
	"""Open another folio on the stay, for example for a company or a companion."""
	frappe.db.get_value(STAY, stay_name, "name", for_update=True)
	stay = _row(STAY, stay_name, ["name", "property", "status"])
	if not stay:
		frappe.throw(_("Stay Reservation {0} does not exist.").format(stay_name), frappe.DoesNotExistError)
	if stay.status in CLOSED_STAY_STATUSES:
		frappe.throw(_("Stay {0} is {1}.").format(stay_name, _(stay.status)), SettlementError)
	folio.ensure_default_folio(stay_name)
	limit = cint(frappe.db.get_value("Hotel Property", stay.property, "max_folios_per_stay"))
	if limit and frappe.db.count(folio.FOLIO, {"stay_reservation": stay_name}) >= limit:
		frappe.throw(_("A stay can have at most {0} folios.").format(limit), SettlementError)
	_check_payee(payee_customer, payee_guest_profile)
	doc = folio.create_folio(
		STAY,
		stay_name,
		label=(label or "").strip() or None,
		payee_customer=payee_customer or _guest_customer(payee_guest_profile),
		payee_guest_profile=payee_guest_profile,
	)
	return doc.name


def set_payee(
	folio_name: str, payee_customer: str | None = None, payee_guest_profile: str | None = None
) -> None:
	"""Change who a folio bills. Not after it took a payment: that payment's Payment Entry is
	made out to the payee, and the invoice must be made out to the same Customer."""
	if not (payee_customer or payee_guest_profile):
		frappe.throw(_("Choose a Customer or a guest to bill."), SettlementError)
	_check_payee(payee_customer, payee_guest_profile)
	row = folio.lock_folio(folio_name)
	if row.status not in folio.POSTABLE_STATUSES:
		frappe.throw(_("Folio {0} is {1}.").format(folio_name, _(row.status)), SettlementError)
	if frappe.db.exists("Folio Payment Allocation", {"guest_folio": folio_name, "docstatus": 1}):
		frappe.throw(
			_("Folio {0} has payments, so its payee can't change. Open another folio instead.").format(
				folio_name
			),
			SettlementError,
		)
	doc = frappe.get_doc(folio.FOLIO, folio_name)
	before = doc.payee_name
	customer = payee_customer or _guest_customer(payee_guest_profile)
	doc.update(
		{
			"payee_customer": customer,
			"payee_guest_profile": payee_guest_profile,
			"payee_name": folio._payee_name(customer, payee_guest_profile),
		}
	)
	doc.flags[folio.SERVICE_FLAG] = True
	doc.save(ignore_permissions=True)
	log_event(folio.FOLIO, folio_name, "Payee Changed", data={"from": before, "to": doc.payee_name})


def _check_payee(customer: str | None, guest_profile: str | None) -> None:
	if customer and not frappe.db.exists("Customer", customer):
		frappe.throw(_("Customer {0} does not exist.").format(customer), frappe.DoesNotExistError)
	if guest_profile and not frappe.db.exists("Guest Profile", guest_profile):
		frappe.throw(_("Guest Profile {0} does not exist.").format(guest_profile), frappe.DoesNotExistError)


def _guest_customer(guest_profile: str | None) -> str | None:
	return frappe.db.get_value("Guest Profile", guest_profile, "customer") if guest_profile else None


# --------------------------------------------------------------------------- transfers


TRANSFER_FIELDS = [
	"name",
	"docstatus",
	"guest_folio",
	"stay_reservation",
	"hotel_booking",
	"direction",
	"transaction_type",
	"charge_code",
	"item",
	"description_snapshot",
	"quantity",
	"unit_rate",
	"gross_amount",
	"tax_amount",
	"tax_breakdown",
	"service_date",
	"stay_guest",
	"reverses",
	"sales_invoice",
	"currency",
]


@folio._retryable
def transfer(
	transaction: str,
	to_folio: str,
	amount=None,
	*,
	reason: str | None = None,
	request_id: str | None = None,
) -> dict:
	"""Move a charge, or `amount` of it, to another folio of the same stay or booking.

	Returns {"out", "in"}: the credit on the source folio and the debit on the target. The same
	`request_id` returns the same pair.
	"""
	line = _row(folio.TRANSACTION, transaction, TRANSFER_FIELDS)
	if not line or line.docstatus != 1:
		frappe.throw(_("Folio Transaction {0} does not exist.").format(transaction), frappe.DoesNotExistError)
	if line.direction != folio.DEBIT or line.transaction_type != folio.REVENUE or line.reverses:
		frappe.throw(_("Only charges can move to another folio."), SettlementError)
	if line.sales_invoice:
		frappe.throw(
			_("{0} is on invoice {1} and can't move.").format(line.name, line.sales_invoice), SettlementError
		)
	if line.guest_folio == to_folio:
		frappe.throw(_("Choose a different folio to move the charge to."), SettlementError)

	# Lock both folios in name order, so two transfers between the same folios can't deadlock.
	rows = {name: folio.lock_folio(name) for name in sorted((line.guest_folio, to_folio))}
	source, target = rows[line.guest_folio], rows[to_folio]
	same_stay = source.stay_reservation and source.stay_reservation == target.stay_reservation
	same_booking = source.hotel_booking and source.hotel_booking == target.hotel_booking
	if not (same_stay or same_booking):
		frappe.throw(_("A charge can only move to a folio of the same stay or booking."), SettlementError)
	for row in (source, target):
		if row.status not in folio.POSTABLE_STATUSES:
			frappe.throw(_("Folio {0} is {1}.").format(row.name, _(row.status)), SettlementError)

	request_id = (request_id or "").strip() or frappe.generate_hash(length=16)
	key = f"xfer:{line.name}:{request_id}"
	done = frappe.db.get_value(folio.TRANSACTION, {"posting_key": f"{key}:in"}, "name")
	if done:
		return {"out": frappe.db.get_value(folio.TRANSACTION, {"posting_key": f"{key}:out"}), "in": done}
	if frappe.db.exists(folio.TRANSACTION, {"reverses": line.name, "docstatus": 1}):
		frappe.throw(_("{0} is reversed and can't move.").format(line.name), SettlementError)
	if frappe.db.exists(folio.TRANSACTION, {"posting_key": ["like", f"alw:{line.name}:%"], "docstatus": 1}):
		frappe.throw(
			_("A package allowance covers {0}, so it stays on its folio.").format(line.name), SettlementError
		)

	part = _transfer_part(line, amount)
	common = {
		"quantity": part["quantity"],
		"unit_rate": line.unit_rate,
		"tax_amount": from_minor(part["tax"], line.currency),
		"tax_breakdown": part["breakdown"],
		"item": line.item,
		# The guest still received it on the original date.
		"service_date": line.service_date,
		"transfer_of": line.name,
		"reason": (reason or "").strip() or None,
		"approved_by": frappe.session.user,
		"is_manual": True,
	}
	gross = from_minor(part["gross"], line.currency)
	target_label = frappe.db.get_value(folio.FOLIO, to_folio, "folio_label")
	moved_out = folio.post(
		line.guest_folio,
		line.charge_code,
		gross,
		posting_key=f"{key}:out",
		direction=folio.CREDIT,
		description=_("Moved to {0}: {1}").format(target_label, line.description_snapshot),
		stay_guest=line.stay_guest,
		transfer_folio=to_folio,
		**common,
	)
	moved_in = folio.post(
		to_folio,
		line.charge_code,
		gross,
		posting_key=f"{key}:in",
		direction=folio.DEBIT,
		description=line.description_snapshot,
		# The consumer stays on the line if the target folio is on the same stay.
		stay_guest=line.stay_guest if same_stay else None,
		transfer_folio=line.guest_folio,
		**common,
	)
	log_event(
		folio.FOLIO,
		line.guest_folio,
		"Charge Transferred",
		reason=common["reason"],
		data={
			"transaction": line.name,
			"to": to_folio,
			"amount": gross,
			"lines": [moved_out["name"], moved_in["name"]],
		},
		property_name=source.property,
	)
	return {"out": moved_out["name"], "in": moved_in["name"]}


def _transfer_part(line, amount) -> dict:
	"""The gross, tax, tax per account, and quantity of the part that moves, in minor units.

	Moving everything that is left takes exactly what is left, so the parts always add up to the
	line, to the minor unit.
	"""
	currency = line.currency
	moved = frappe.get_all(
		folio.TRANSACTION,
		filters={"transfer_of": line.name, "direction": folio.CREDIT, "docstatus": 1},
		fields=["gross_amount", "tax_amount", "tax_breakdown", "quantity"],
	)
	gross_total = to_minor(line.gross_amount, currency)
	tax_total = to_minor(line.tax_amount, currency)
	breakdown_total = _breakdown_minor(line, currency)
	left_gross = gross_total - sum(to_minor(row.gross_amount, currency) for row in moved)
	left_tax = tax_total - sum(to_minor(row.tax_amount, currency) for row in moved)
	left_breakdown = dict(breakdown_total)
	for row in moved:
		for account, value in _breakdown_minor(row, currency).items():
			left_breakdown[account] -= value
	left_quantity = flt(line.quantity) - sum(flt(row.quantity) for row in moved)

	part_gross = left_gross if amount in (None, "") else to_minor(amount, currency)
	if part_gross <= 0 or part_gross > left_gross:
		frappe.throw(
			_("Move more than zero and at most {0}.").format(from_minor(left_gross, currency)),
			SettlementError,
		)
	if part_gross == left_gross:
		return {
			"gross": left_gross,
			"tax": left_tax,
			"breakdown": _breakdown_rows(line, left_breakdown, currency),
			"quantity": left_quantity or flt(line.quantity),
		}

	share = Decimal(part_gross) / Decimal(gross_total)
	tax = _round(Decimal(tax_total) * share)
	breakdown = {account: _round(Decimal(value) * share) for account, value in breakdown_total.items()}
	if breakdown:
		# The per-account parts add up to the part's tax; the largest account absorbs rounding.
		largest = max(breakdown, key=lambda account: abs(breakdown_total[account]))
		breakdown[largest] += tax - sum(breakdown.values())
	return {
		"gross": part_gross,
		"tax": min(tax, left_tax),
		"breakdown": _breakdown_rows(line, breakdown, currency),
		"quantity": round(flt(line.quantity) * float(share), 6) or 1,
	}


def _round(value: Decimal) -> int:
	return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _breakdown(line) -> list[dict]:
	return frappe.parse_json(line.tax_breakdown) if line.tax_breakdown else []


def _breakdown_minor(line, currency: str) -> dict[str, int]:
	"""The line's tax per account, in minor units. The rows add up to the line's tax."""
	totals: dict[str, int] = defaultdict(int)
	for row in _breakdown(line):
		totals[row["account"]] += to_minor(row["amount"], currency)
	tax = to_minor(line.tax_amount, currency)
	if tax and not totals:
		frappe.throw(
			_("Line {0} has tax but no tax accounts, so it can't be invoiced or split.").format(line.name),
			SettlementError,
		)
	if totals and sum(totals.values()) != tax:
		# ERPNext rounds each tax row; keep the line's tax as the total.
		last = list(totals)[-1]
		totals[last] += tax - sum(totals.values())
	return dict(totals)


def _breakdown_rows(line, amounts: dict[str, int], currency: str) -> list[dict]:
	descriptions = {row["account"]: row.get("description") for row in _breakdown(line)}
	return [
		{"account": account, "description": descriptions.get(account), "amount": from_minor(value, currency)}
		for account, value in amounts.items()
		if value
	]


# --------------------------------------------------------------------------- invoice lines


INVOICE_LINE_FIELDS = [
	"name",
	"direction",
	"transaction_type",
	"item",
	"print_group",
	"description_snapshot",
	"net_amount",
	"tax_amount",
	"gross_amount",
	"tax_breakdown",
	"accounting_mode",
	"sales_invoice",
]


def billable_lines(folio_name: str, currency: str) -> list:
	"""The folio's lines the invoice bills: posted, not invoiced yet, not money in, and not
	already accounted for by another document (design §17.2)."""
	return [
		row
		for row in folio._locked_lines(folio_name, *INVOICE_LINE_FIELDS)
		if not row.sales_invoice
		and row.transaction_type not in PAYMENT_TYPES
		and row.accounting_mode != EXTERNALLY_ACCOUNTED
	]


def invoice_lines(lines, currency: str) -> dict:
	"""Group `lines` into invoice lines and tax rows, in minor units.

	Returns {"items": [{item, description, net}], "taxes": [{account, description, amount}],
	"net", "tax", "gross", "lines": [names]}.
	"""
	items: dict[tuple, int] = defaultdict(int)
	taxes: dict[str, int] = defaultdict(int)
	tax_descriptions: dict[str, str] = {}
	names = []
	item_names = {}
	for row in lines:
		sign = 1 if row.direction == folio.DEBIT else -1
		gross = to_minor(row.gross_amount, currency)
		if not gross:
			continue
		if not row.item:
			frappe.throw(
				_("Line {0} ({1}) has no Item, so it can't be invoiced.").format(
					row.name, row.description_snapshot
				),
				SettlementError,
			)
		if row.item not in item_names:
			item_names[row.item] = frappe.db.get_value("Item", row.item, "item_name")
		label = row.print_group or item_names[row.item]
		items[(row.item, label)] += sign * to_minor(row.net_amount, currency)
		for account, value in _breakdown_minor(row, currency).items():
			taxes[account] += sign * value
		for entry in _breakdown(row):
			tax_descriptions.setdefault(entry["account"], entry.get("description") or entry["account"])
		names.append(row.name)

	for (_item, label), net in items.items():
		if net < 0:
			frappe.throw(
				_("Credits on {0} are more than its charges. Check the reversals and transfers.").format(
					label
				),
				SettlementError,
			)
	for account, value in taxes.items():
		if value < 0:
			frappe.throw(_("Tax on {0} comes out below zero.").format(account), SettlementError)
	net = sum(items.values())
	tax = sum(taxes.values())
	return {
		"items": [
			{"item": item, "description": label, "net": value}
			for (item, label), value in items.items()
			if value
		],
		"taxes": [
			{"account": account, "description": tax_descriptions.get(account, account), "amount": value}
			for account, value in taxes.items()
			if value
		],
		"net": net,
		"tax": tax,
		"gross": net + tax,
		"lines": names,
	}


def _folio_advances(folio_name: str, currency: str) -> dict[str, int]:
	"""What each Payment Entry paid toward this folio, less what was refunded from it, in minor
	units. These become the invoice's advances."""
	allocations = frappe.get_all(
		"Folio Payment Allocation",
		filters={"guest_folio": folio_name, "docstatus": 1},
		fields=["name", "payment_entry", "direction", "amount", "refund_of_allocation"],
	)
	refunded: dict[str, int] = defaultdict(int)
	for row in allocations:
		if row.direction == folio.DEBIT and row.refund_of_allocation:
			refunded[row.refund_of_allocation] += to_minor(row.amount, currency)
	paid: dict[str, int] = defaultdict(int)
	for row in allocations:
		if row.direction == folio.CREDIT:
			paid[row.payment_entry] += to_minor(row.amount, currency) - refunded[row.name]
	return {entry: amount for entry, amount in paid.items() if amount > 0}


def preview(folio_name: str) -> dict:
	"""What settling the folio would invoice now, for the Folio Workspace."""
	row = _row(folio.FOLIO, folio_name, ["name", "currency", "balance", "sales_invoice"])
	currency = row.currency
	lines = invoice_lines(billable_lines(folio_name, currency), currency)
	paid = sum(_folio_advances(folio_name, currency).values())
	return {
		"items": [{**line, "net": from_minor(line["net"], currency)} for line in lines["items"]],
		"taxes": [{**line, "amount": from_minor(line["amount"], currency)} for line in lines["taxes"]],
		"net": from_minor(lines["net"], currency),
		"tax": from_minor(lines["tax"], currency),
		"total": from_minor(lines["gross"], currency),
		"paid": from_minor(paid, currency),
		"outstanding": from_minor(lines["gross"] - paid, currency),
		"balance": row.balance,
	}


# --------------------------------------------------------------------------- settlement


@folio._retryable
def settle(folio_name: str, *, transfer_to_ar: bool = False, override_reason: str | None = None) -> dict:
	"""Invoice the folio and close it, or leave its balance as the company's receivable.

	Returns {"status", "sales_invoice", "error"}. A rejected submission returns status Settlement
	Pending with the error rather than raising, so the folio keeps that status.
	"""
	row = folio.lock_folio(folio_name)
	if not frappe.db.get_value(folio.FOLIO, folio_name, "sales_invoice"):
		# Check-out cancels unused nights; count what is really still to post.
		folio.refresh_pending(folio_name)
	doc = frappe.get_doc(folio.FOLIO, folio_name)
	if doc.sales_invoice:
		return _result(doc)
	if doc.status not in SETTLEABLE_STATUSES:
		frappe.throw(_("Folio {0} is {1}.").format(folio_name, _(doc.status)), SettlementError)
	currency = row.currency
	if to_minor(doc.pending_total, currency):
		frappe.throw(
			_("Folio {0} has nights not charged yet. Check the guest out or run night audit first.").format(
				folio_name
			),
			SettlementError,
		)
	if frappe.db.exists(
		"Folio Payment Split",
		{"guest_folio": folio_name, "parenttype": "Folio Payment", "parent": ["in", _pending_payments()]},
	):
		frappe.throw(_("A phone payment for folio {0} is still waiting.").format(folio_name), SettlementError)

	lines = invoice_lines(billable_lines(folio_name, currency), currency)
	advances = _folio_advances(folio_name, currency)
	outstanding = lines["gross"] - sum(advances.values())
	balance = to_minor(row.balance, currency)
	if outstanding != balance:
		frappe.throw(
			_(
				"The folio balance ({0}) doesn't match what the invoice would leave unpaid ({1}). "
				"Check for lines accounted elsewhere, or rebuild the folio balance."
			).format(from_minor(balance, currency), from_minor(outstanding, currency)),
			SettlementError,
		)
	if outstanding < 0:
		frappe.throw(
			_("The guest paid {0} too much. Refund it first.").format(from_minor(-outstanding, currency)),
			SettlementError,
		)
	if outstanding and not transfer_to_ar:
		frappe.throw(
			_("Folio {0} still owes {1}. Take a payment, or transfer it to the company's account.").format(
				folio_name, from_minor(outstanding, currency)
			),
			SettlementError,
		)
	if transfer_to_ar and not outstanding:
		frappe.throw(_("Folio {0} has nothing owing to transfer.").format(folio_name), SettlementError)

	if not lines["items"]:
		# Nothing to bill and nothing paid: close it without an invoice.
		_close(doc, reason=_("Nothing to invoice"))
		return _result(doc)

	from frappoint.vuna_hospitality.services.cashiering import payer_for

	customer = payer_for(folio_name)
	company = frappe.db.get_value("Hotel Property", doc.property, "company")
	if transfer_to_ar:
		_check_ar_transfer(doc, customer, company, outstanding, override_reason)

	invoice = _sales_invoice(doc, customer, company, lines)
	_add_advances(invoice, advances, currency)

	messages = len(frappe.local.message_log)
	frappe.db.savepoint(SAVEPOINT)
	try:
		invoice.insert(ignore_permissions=True)
		_check_total(invoice, lines["gross"], currency)
		invoice.flags.ignore_permissions = True
		invoice.submit()
	except frappe.ValidationError as error:
		frappe.db.rollback(save_point=SAVEPOINT)
		del frappe.local.message_log[messages:]
		return _pending(doc, error)

	_link_lines(lines["lines"], invoice.name)
	updates = {
		"sales_invoice": invoice.name,
		"settled_at": now_datetime(),
		"settled_by": frappe.session.user,
		"settlement_error": None,
	}
	data = {"sales_invoice": invoice.name, "total": from_minor(lines["gross"], currency)}
	if transfer_to_ar:
		transition(
			doc,
			TRANSFERRED_TO_AR,
			reason=override_reason,
			updates={**updates, "closed_at": now_datetime(), "closed_by": frappe.session.user},
			data={**data, "outstanding": from_minor(outstanding, currency), "customer": customer},
			event_type="Folio Transferred to AR",
			ignore_permissions=True,
		)
	else:
		transition(
			doc, SETTLED, updates=updates, data=data, event_type="Folio Settled", ignore_permissions=True
		)
		# Post-stay charges (F12) will keep a settled folio open for a while; for now it closes.
		_close(doc)
	return _result(doc)


def _pending_payments() -> list[str]:
	return frappe.get_all("Folio Payment", filters={"status": "Pending"}, pluck="name") or [""]


def _close(doc, reason: str | None = None) -> None:
	transition(
		doc,
		folio.CLOSED,
		reason=reason,
		updates={"closed_at": now_datetime(), "closed_by": frappe.session.user, "pending_total": 0},
		event_type="Folio Closed",
		ignore_permissions=True,
	)


def _pending(doc, error) -> dict:
	message = strip_html(str(error)) or _("The Sales Invoice was rejected.")
	if doc.status == SETTLEMENT_PENDING:
		doc.flags[folio.SERVICE_FLAG] = True
		doc.db_set("settlement_error", message)
		log_event(folio.FOLIO, doc.name, "Settlement Rejected", reason=message)
	else:
		transition(
			doc,
			SETTLEMENT_PENDING,
			reason=message,
			updates={"settlement_error": message},
			event_type="Settlement Rejected",
			ignore_permissions=True,
		)
	return _result(doc)


def _result(doc) -> dict:
	return {
		"folio": doc.name,
		"status": doc.status,
		"sales_invoice": doc.sales_invoice,
		"error": doc.settlement_error,
	}


def _check_ar_transfer(
	doc, customer: str, company: str, outstanding: int, override_reason: str | None
) -> None:
	"""A balance goes to a company's receivable, within its ERPNext credit limit (§17.4).

	Over the limit, only the role set as Credit Controller in Accounts Settings can go ahead, with a
	reason: ERPNext checks the same limit when the invoice is submitted and lets that role through.
	"""
	from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding

	if not set(FOLIO_ACCOUNTING_ROLES) & set(frappe.get_roles()):
		frappe.throw(
			_("You aren't allowed to transfer a folio to a company's account."), frappe.PermissionError
		)
	if frappe.db.get_value("Customer", customer, "customer_type") != "Company":
		frappe.throw(
			_(
				"Only a company can be billed on account. {0} is an individual: take the payment instead."
			).format(frappe.db.get_value("Customer", customer, "customer_name")),
			SettlementError,
		)
	limit = flt(get_credit_limit(customer, company))
	if not limit:
		return
	amount = from_minor(outstanding, doc.currency)
	owed = flt(get_customer_outstanding(customer, company)) + amount
	if owed <= limit:
		return
	controller = frappe.db.get_single_value("Accounts Settings", "credit_controller")
	over = _("This takes {0} to {1}, over its credit limit of {2}.").format(customer, owed, limit)
	if not controller or controller not in frappe.get_roles():
		frappe.throw(
			over
			+ " "
			+ _("Ask someone with the {0} role to approve it.").format(controller or _("Credit Controller")),
			CreditLimitError,
		)
	if not (override_reason or "").strip():
		frappe.throw(over + " " + _("Give a reason to approve it."), CreditLimitError)
	log_event(
		folio.FOLIO,
		doc.name,
		"Credit Limit Override",
		reason=override_reason.strip(),
		data={"customer": customer, "credit_limit": limit, "outstanding_after": owed},
	)


def _sales_invoice(doc, customer: str, company: str, lines: dict, *, is_return: bool = False):
	"""An unsaved Sales Invoice for `lines`: one row per Item and print group, the folio's own tax
	amounts as Actual rows, and the booking's sales partner for commission (feature FB).

	A credit note (`is_return`) stands on its own rather than naming the original in
	`return_against`: ERPNext limits returns to each original row's quantity, and a grouped row
	(one "Food and Beverage" line) may need several corrections."""
	prop = _row("Hotel Property", doc.property, ["business_date", "default_cost_center"])
	currency = doc.currency
	sign = -1 if is_return else 1
	invoice = frappe.new_doc("Sales Invoice")
	invoice.update(
		{
			"customer": customer,
			"company": company,
			"currency": currency,
			"conversion_rate": 1,
			"price_list_currency": currency,
			"plc_conversion_rate": 1,
			"ignore_pricing_rule": 1,
			"set_posting_time": 1,
			"posting_date": prop.business_date,
			"due_date": prop.business_date,
			"cost_center": prop.default_cost_center,
			"custom_guest_folio": doc.name,
			"remarks": _("Hotel folio {0} ({1})").format(doc.name, doc.folio_label),
		}
	)
	if is_return:
		invoice.is_return = 1
	booking = doc.hotel_booking and _row(BOOKING, doc.hotel_booking, ["sales_partner"])
	if booking and booking.sales_partner:
		invoice.sales_partner = booking.sales_partner
		invoice.commission_rate = frappe.db.get_value(
			"Sales Partner", booking.sales_partner, "commission_rate"
		)
	for line in lines["items"]:
		rate = from_minor(line["net"], currency)
		invoice.append(
			"items",
			{
				"item_code": line["item"],
				# The print group, so a company's invoice doesn't list each item.
				"item_name": line["description"][:140],
				"description": line["description"],
				"qty": sign,
				"rate": rate,
				"price_list_rate": rate,
				"conversion_factor": 1,
				"cost_center": prop.default_cost_center,
			},
		)
	taxes = [
		{
			"charge_type": "Actual",
			"account_head": tax["account"],
			"description": tax["description"],
			"tax_amount": sign * from_minor(tax["amount"], currency),
			"included_in_print_rate": 0,
			"cost_center": prop.default_cost_center,
		}
		for tax in lines["taxes"]
	]
	invoice.flags.ignore_permissions = True
	invoice.set_missing_values()
	# The taxes are the folio's own. Set them after ERPNext fills in the defaults, so a default
	# Sales Taxes and Charges Template can't add more.
	invoice.taxes_and_charges = None
	invoice.set("taxes", taxes)
	invoice.calculate_taxes_and_totals()
	return invoice


def _add_advances(invoice, advances: dict[str, int], currency: str) -> None:
	"""Attach the folio's payments to the invoice, from ERPNext's own list of open advances."""
	if not advances:
		return
	available = {
		entry.reference_name: entry
		for entry in invoice.get_advance_entries()
		if entry.reference_type == "Payment Entry" and entry.reference_name in advances
	}
	for name, amount in advances.items():
		entry = available.get(name)
		if not entry or to_minor(entry.amount, currency) < amount:
			party = frappe.db.get_value("Payment Entry", name, "party")
			frappe.throw(
				_(
					"Payment {0} was received from {1}, not from the folio's payee {2}, or is already used. "
					"Settle it on its payer's folio."
				).format(name, party, invoice.customer),
				SettlementError,
			)
		row = {
			"reference_type": "Payment Entry",
			"reference_name": name,
			"reference_row": entry.reference_row,
			"remarks": entry.remarks,
			"advance_amount": flt(entry.amount),
			"allocated_amount": from_minor(amount, currency),
			"ref_exchange_rate": flt(entry.exchange_rate) or 1,
			"difference_posting_date": invoice.posting_date,
		}
		if entry.get("paid_from"):
			row["account"] = entry.paid_from
		invoice.append("advances", row)
	invoice.calculate_taxes_and_totals()


def _check_total(invoice, expected_minor: int, currency: str) -> None:
	total = to_minor(abs(flt(invoice.grand_total)), currency)
	if total != abs(expected_minor):
		frappe.throw(
			_("The invoice total {0} doesn't match the folio's charges {1}.").format(
				invoice.grand_total, from_minor(expected_minor, currency)
			),
			SettlementError,
		)


def _link_lines(names: list[str], invoice: str) -> None:
	if not names:
		return
	table = frappe.qb.DocType(folio.TRANSACTION)
	frappe.qb.update(table).set(table.sales_invoice, invoice).where(table.name.isin(names)).run()


def release_settlement(folio_name: str, reason: str) -> None:
	"""Reopen a folio whose settlement was rejected, to correct it before settling again."""
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for reopening the folio."), SettlementError)
	folio.lock_folio(folio_name)
	doc = frappe.get_doc(folio.FOLIO, folio_name)
	if doc.status != SETTLEMENT_PENDING:
		frappe.throw(_("Folio {0} is {1}.").format(folio_name, _(doc.status)), SettlementError)
	transition(
		doc,
		folio.OPEN,
		reason=reason,
		updates={"settlement_error": None},
		event_type="Folio Reopened",
		ignore_permissions=True,
	)


# --------------------------------------------------------------------------- credit notes


@folio._retryable
def credit_note(transaction: str, reason: str) -> dict:
	"""Correct an invoiced charge: reverse it on the folio and issue a linked credit note.

	The original invoice is left as it is. Returns {"reversal", "credit_note"}; asking again for the
	same charge returns the same pair.
	"""
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for the credit note."), SettlementError)
	line = _row(
		folio.TRANSACTION,
		transaction,
		[*TRANSFER_FIELDS, "net_amount", "print_group", "transaction_type"],
	)
	if not line or line.docstatus != 1:
		frappe.throw(_("Folio Transaction {0} does not exist.").format(transaction), frappe.DoesNotExistError)
	if not line.sales_invoice:
		frappe.throw(_("{0} isn't invoiced yet. Reverse it instead.").format(line.name), SettlementError)
	if line.direction != folio.DEBIT or line.reverses or line.transaction_type != folio.REVENUE:
		frappe.throw(_("Only an invoiced charge can be credited."), SettlementError)
	if frappe.db.get_value("Sales Invoice", line.sales_invoice, "is_return"):
		frappe.throw(_("{0} is itself on a credit note.").format(line.name), SettlementError)
	if frappe.db.exists(folio.TRANSACTION, {"posting_key": ["like", f"alw:{line.name}:%"], "docstatus": 1}):
		frappe.throw(
			_("A package allowance covered {0}, so the invoice billed nothing for it.").format(line.name),
			SettlementError,
		)

	folio.lock_folio(line.guest_folio)
	existing = frappe.db.get_value(
		folio.TRANSACTION, {"posting_key": f"rev:{line.name}"}, ["name", "sales_invoice"], as_dict=True
	)
	if existing and existing.sales_invoice:
		return {"reversal": existing.name, "credit_note": existing.sales_invoice}

	doc = frappe.get_doc(folio.FOLIO, line.guest_folio)
	reversal = (
		existing.name
		if existing
		else folio.post(
			line.guest_folio,
			line.charge_code,
			line.gross_amount,
			posting_key=f"rev:{line.name}",
			direction=folio.CREDIT,
			quantity=line.quantity,
			unit_rate=line.unit_rate,
			tax_amount=line.tax_amount,
			tax_breakdown=_breakdown(line) or None,
			item=line.item,
			description=_("Credit note: {0}").format(line.description_snapshot),
			service_date=line.service_date,
			stay_guest=line.stay_guest,
			reverses=line.name,
			reason=reason,
			approved_by=frappe.session.user,
			is_manual=True,
			allow_closed=True,
		)["name"]
	)
	# The credit note bills the reversal as the invoice billed the charge.
	charged = frappe._dict({**line, "direction": folio.DEBIT, "sales_invoice": None})
	lines = invoice_lines([charged], doc.currency)
	lines["lines"] = [reversal]
	customer = frappe.db.get_value("Sales Invoice", line.sales_invoice, "customer")
	company = frappe.db.get_value("Sales Invoice", line.sales_invoice, "company")
	note = _sales_invoice(doc, customer, company, lines, is_return=True)
	note.remarks = _("Credit note against {0} for {1} on hotel folio {2}: {3}").format(
		line.sales_invoice, line.name, doc.name, reason
	)
	messages = len(frappe.local.message_log)
	frappe.db.savepoint(SAVEPOINT)
	try:
		note.insert(ignore_permissions=True)
		_check_total(note, lines["gross"], doc.currency)
		note.flags.ignore_permissions = True
		note.submit()
	except frappe.ValidationError as error:
		frappe.db.rollback(save_point=SAVEPOINT)
		del frappe.local.message_log[messages:]
		frappe.throw(_("The credit note was rejected: {0}").format(strip_html(str(error))), SettlementError)
	_link_lines([reversal], note.name)
	log_event(
		folio.FOLIO,
		doc.name,
		"Credit Note Issued",
		reason=reason,
		data={
			"transaction": line.name,
			"reversal": reversal,
			"credit_note": note.name,
			"against": line.sales_invoice,
		},
	)
	return {"reversal": reversal, "credit_note": note.name}
