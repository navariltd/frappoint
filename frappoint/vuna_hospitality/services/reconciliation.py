"""Night audit's Reconcile stage: do the books agree with themselves? (design §21.1; plan F19)

It changes nothing. Each check returns the problems it found:

- **Postings**: every in-house night of the closing date was posted (or waived), and every posted
  night's folio line exists.
- **Folio totals**: each open folio's cached debits, credits and balance equal its lines.
- **Payments**: each received payment is allocated to folios in full, each allocation has its
  folio line, and the payment's Payment Entry is submitted. A payment line reversed on the folio
  without a refund is a difference too: the folio and the Payment Entry no longer agree.
- **Cashier shifts**: a shift closed on the closing date has a reason for every variance.
- **Deposits**: a deposit's status agrees with what its payments hold.
- **Inventory**: the room counters for the closing date and the next night match the bookings.

A problem fails the stage, and the run keeps its checkpoint: after investigating, run the audit
again and only this stage onwards repeats. A manager can let the differences pass with a reason.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, getdate

from frappoint.vuna_hospitality.services.money import to_minor

STAY = "Stay Reservation"
NIGHT = "Stay Rate Night"
TRANSACTION = "Folio Transaction"
FOLIO = "Guest Folio"
PAYMENT = "Folio Payment"
ALLOCATION = "Folio Payment Allocation"
SHIFT = "Cashier Shift"
DEPOSIT = "Guest Deposit"
IN_HOUSE_STATUSES = ("In House", "Due Out")
POSTABLE_FOLIO_STATUSES = ("Open", "Settlement Pending")
OPEN_DEPOSIT_STATUSES = ("Requested", "Partly Paid", "Received")


def _problem(check: str, label: str, name: str | None = None, doctype: str | None = None) -> dict:
	return {"check": check, "label": label, "name": name, "doctype": doctype}


def postings(property_name: str, business_date) -> list[dict]:
	night = frappe.qb.DocType(NIGHT)
	stay = frappe.qb.DocType(STAY)
	rows = (
		frappe.qb.from_(night)
		.join(stay)
		.on(stay.name == night.stay_reservation)
		.select(
			night.name, night.posting_state, night.posting_key, stay.name.as_("stay"), stay.lead_guest_name
		)
		.where(night.property == property_name)
		.where(night.night_date == getdate(business_date))
		.where(stay.status.isin(IN_HOUSE_STATUSES))
	).run(as_dict=True)
	problems = []
	posted_keys = [row.posting_key for row in rows if row.posting_state == "Posted" and row.posting_key]
	existing = set(
		frappe.get_all(TRANSACTION, filters={"posting_key": ["in", posted_keys or [""]]}, pluck="posting_key")
	)
	for row in rows:
		guest = row.lead_guest_name or row.stay
		if row.posting_state == "Pending":
			problems.append(
				_problem(
					_("Postings"), _("{0}: tonight's room charge is not posted").format(guest), row.stay, STAY
				)
			)
		elif row.posting_state == "Posted" and row.posting_key not in existing:
			problems.append(
				_problem(
					_("Postings"),
					_("{0}: tonight is marked posted but its folio line is missing").format(guest),
					row.stay,
					STAY,
				)
			)
	return problems


def folio_totals(property_name: str, business_date=None) -> list[dict]:
	folios = frappe.get_all(
		FOLIO,
		filters={"property": property_name, "status": ["in", POSTABLE_FOLIO_STATUSES]},
		fields=[
			"name",
			"currency",
			"posted_debits",
			"posted_credits",
			"balance",
			"transaction_count",
			"payee_name",
		],
	)
	if not folios:
		return []
	sums = defaultdict(lambda: {"Debit": 0, "Credit": 0, "count": 0})
	currencies = {row.name: row.currency for row in folios}
	for line in frappe.get_all(
		TRANSACTION,
		filters={"guest_folio": ["in", list(currencies)], "docstatus": 1},
		fields=["guest_folio", "direction", "gross_amount"],
	):
		entry = sums[line.guest_folio]
		entry[line.direction] += to_minor(line.gross_amount, currencies[line.guest_folio])
		entry["count"] += 1
	problems = []
	for row in folios:
		entry = sums[row.name]
		cached = (
			to_minor(row.posted_debits, row.currency),
			to_minor(row.posted_credits, row.currency),
			to_minor(row.balance, row.currency),
			int(row.transaction_count or 0),
		)
		actual = (entry["Debit"], entry["Credit"], entry["Debit"] - entry["Credit"], entry["count"])
		if cached != actual:
			problems.append(
				_problem(
					_("Folio totals"),
					_("{0}: the folio's totals don't match its lines").format(row.payee_name or row.name),
					row.name,
					FOLIO,
				)
			)
	return problems


def payments(property_name: str, business_date) -> list[dict]:
	"""Payments that reached a folio tonight, and received payments that reached no folio."""
	day = getdate(business_date)
	lines_today = frappe.get_all(
		TRANSACTION,
		filters={
			"property": property_name,
			"docstatus": 1,
			"business_date": day,
			"transaction_type": ["in", ("Payment", "Deposit")],
		},
		pluck="name",
	)
	allocations = frappe.get_all(
		ALLOCATION,
		filters={"folio_transaction": ["in", lines_today or [""]]},
		pluck="folio_payment",
	)
	payment = frappe.qb.DocType(PAYMENT)
	allocation = frappe.qb.DocType(ALLOCATION)
	unallocated = (
		frappe.qb.from_(payment)
		.left_join(allocation)
		.on(allocation.folio_payment == payment.name)
		.select(payment.name)
		.where(payment.property == property_name)
		.where(payment.status == "Received")
		.where(allocation.name.isnull())
	).run(pluck=True)
	payment_names = set(allocations) | set(unallocated)
	problems = []
	for name in sorted(payment_names):
		payment = frappe.db.get_value(
			PAYMENT,
			name,
			["name", "status", "amount", "currency", "payment_entry", "payer_name"],
			as_dict=True,
		)
		if not payment or payment.status != "Received":
			continue
		who = payment.payer_name or payment.name
		rows = frappe.get_all(
			ALLOCATION,
			filters={"folio_payment": name, "docstatus": 1},
			fields=["amount", "folio_transaction"],
		)
		allocated = sum(to_minor(row.amount, payment.currency) for row in rows)
		if allocated != to_minor(payment.amount, payment.currency):
			problems.append(
				_problem(
					_("Payments"),
					_("{0}: payment {1} is not fully on folios").format(who, payment.name),
					payment.name,
					PAYMENT,
				)
			)
		missing = [row for row in rows if not frappe.db.exists(TRANSACTION, row.folio_transaction)]
		if missing:
			problems.append(
				_problem(
					_("Payments"),
					_("{0}: payment {1} has an allocation without its folio line").format(who, payment.name),
					payment.name,
					PAYMENT,
				)
			)
		if (
			payment.payment_entry
			and frappe.db.get_value("Payment Entry", payment.payment_entry, "docstatus") != 1
		):
			problems.append(
				_problem(
					_("Payments"),
					_("{0}: Payment Entry {1} is not submitted").format(who, payment.payment_entry),
					payment.name,
					PAYMENT,
				)
			)
	return problems


def reversed_payment_lines(property_name: str, business_date=None) -> list[dict]:
	"""A payment's folio line reversed while the money was neither refunded nor moved: the folio
	says the guest owes again, but the Payment Entry still holds their money."""
	reversal = frappe.qb.DocType(TRANSACTION)
	allocation = frappe.qb.DocType(ALLOCATION)
	payment = frappe.qb.DocType(PAYMENT)
	rows = (
		frappe.qb.from_(reversal)
		.join(allocation)
		.on(allocation.folio_transaction == reversal.reverses)
		.join(payment)
		.on(payment.name == allocation.folio_payment)
		.select(payment.name, payment.payer_name, allocation.guest_folio, reversal.gross_amount)
		.where(reversal.property == property_name)
		.where(reversal.docstatus == 1)
		.where(reversal.transaction_type.isin(("Payment", "Deposit")))
		.where(payment.status == "Received")
	).run(as_dict=True)
	problems = []
	for row in rows:
		refunded = frappe.db.exists(PAYMENT, {"refund_of": row.name, "status": "Received"})
		if not refunded:
			problems.append(
				_problem(
					_("Payments"),
					_(
						"{0}: payment {1}'s line on folio {2} was reversed, but the money wasn't refunded"
					).format(row.payer_name or row.name, row.name, row.guest_folio),
					row.name,
					PAYMENT,
				)
			)
	return problems


def cashier_shifts(property_name: str, business_date) -> list[dict]:
	problems = []
	for shift in frappe.get_all(
		SHIFT,
		filters={
			"property": property_name,
			"business_date": getdate(business_date),
			"status": ["in", ("Closed", "Reviewed")],
		},
		fields=["name", "cashier", "currency"],
	):
		for count in frappe.get_all(
			"Cashier Shift Count",
			filters={"parent": shift.name, "parenttype": SHIFT},
			fields=["mode_of_payment", "variance", "variance_reason"],
		):
			if to_minor(count.variance, shift.currency) and not (count.variance_reason or "").strip():
				problems.append(
					_problem(
						_("Cashier shifts"),
						_("{0}: {1} is out by {2} with no reason").format(
							shift.cashier, count.mode_of_payment, count.variance
						),
						shift.name,
						SHIFT,
					)
				)
	return problems


def deposits(property_name: str, business_date=None) -> list[dict]:
	from frappoint.vuna_hospitality.services import deposits as deposit_service

	problems = []
	for row in frappe.get_all(
		DEPOSIT,
		filters={"property": property_name, "status": ["in", OPEN_DEPOSIT_STATUSES]},
		fields=["name", "status", "required_amount", "currency"],
	):
		held = deposit_service.amounts(row.name).held
		required = to_minor(row.required_amount, row.currency)
		expected = "Received" if held >= required else "Partly Paid" if held > 0 else "Requested"
		# A deposit only moves forward: one partly refunded after it came in stays Received.
		order = list(OPEN_DEPOSIT_STATUSES)
		if order.index(expected) > order.index(row.status):
			problems.append(
				_problem(
					_("Deposits"),
					_("Deposit {0} is {1}, but its payments make it {2}").format(
						row.name, _(row.status), _(expected)
					),
					row.name,
					DEPOSIT,
				)
			)
	return problems


def inventory(property_name: str, business_date) -> list[dict]:
	from frappoint.vuna_hospitality.services import inventory as inventory_service

	day = getdate(business_date)
	return [
		_problem(
			_("Inventory"),
			_("{0} on {1}: room counters don't match the bookings").format(
				row["room_type"], frappe.format(row["night"], "Date")
			),
			row["name"],
			"Room Type Inventory Day",
		)
		for row in inventory_service.reconcile(property_name, day, add_days(day, 1))
	]


CHECKS = (postings, folio_totals, payments, reversed_payment_lines, cashier_shifts, deposits, inventory)


def reconcile(property_name: str, business_date) -> list[dict]:
	"""Every difference found, from every check. Empty when the books agree."""
	problems = []
	for check in CHECKS:
		problems += check(property_name, business_date)
	return problems
