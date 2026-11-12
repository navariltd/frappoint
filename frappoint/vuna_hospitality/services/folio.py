"""Guest folios and the posting engine (design §15, §28.3, §28.5, §30.16-30.17; feature F7).

A **Guest Folio** is the running tab of one payee. A stay gets its default folio when it is
confirmed. Every line on a folio is a **Folio Transaction**: submitted when it is created, and
never edited, cancelled, or deleted afterwards. A wrong line is corrected by a reversal, which is a
new transaction in the opposite direction.

`post()` is the only way to create a Folio Transaction. It gives exactly-once posting through the
transaction's unique `posting_key` (formats in §28.5, e.g. `night:<stay>:<date>:room`):

1. Lock the folio row, so postings to one folio run one after another.
2. Insert the transaction. If the key is taken, roll back to a savepoint and return the existing
   transaction instead. The unique index is the guarantee; nothing checks first and inserts later.
3. Add the amount to the folio's cached totals and write an audit event.

Staff post by **Item**, as on a Quotation; `resolve_charge_code()` finds the code: a code whose
fixed Item is that Item, else the code covering the Item's Item Group (the nearest group wins).

Cached totals are a fast summary. The transactions are the truth: `rebuild_folio_balance()`
recomputes the totals from them. Amounts are added in integer minor units, so totals never drift.
"""

from decimal import Decimal

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.utils import cint, flt, getdate, now_datetime

from frappoint.vuna_hospitality.constants import FOLIO_MANAGER_ROLES
from frappoint.vuna_hospitality.doctype.charge_code.charge_code import income_account, is_in_group
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.inventory import InventoryConflictError
from frappoint.vuna_hospitality.services.money import from_minor, to_minor
from frappoint.vuna_hospitality.services.reservations import BOOKING, RATE_NIGHT, STAY, _row
from frappoint.vuna_hospitality.services.status_commands import transition

FOLIO = "Guest Folio"
TRANSACTION = "Folio Transaction"
CHARGE_CODE = "Charge Code"
STAY_GUEST = "Stay Guest"

OPEN, CLOSED = "Open", "Closed"
POST_STAY_OPEN = "Post-Stay Open"
# Statuses a folio accepts postings in. Settlement (F11) and post-stay folios (F12) use the rest.
POSTABLE_STATUSES = (OPEN, POST_STAY_OPEN)
DEBIT, CREDIT = "Debit", "Credit"
REVENUE = "Revenue"
ITEM_TYPES = ("Revenue", "Allowance")

# The direction a code posts in. Transfer and Adjustment go either way, so the caller says which.
NATURAL_DIRECTION = {
	"Revenue": DEBIT,
	"Paid-out": DEBIT,
	"Payment": CREDIT,
	"Deposit": CREDIT,
	"Allowance": CREDIT,
	"Write-off": CREDIT,
}
OPPOSITE = {DEBIT: CREDIT, CREDIT: DEBIT}

POSTING_KEY_LENGTH = 140
DEFAULT_FOLIO_LABEL = "Guest"
SAVEPOINT = "folio_posting"

# Set on records created by this service; the DocTypes refuse writes without it.
SERVICE_FLAG = "from_posting_service"

CODE_FIELDS = (
	"name",
	"description",
	"transaction_type",
	"is_active",
	"is_room_revenue",
	"print_group",
	"item",
	"item_group",
	"accounting_mode",
	"allow_manual_posting",
	"allow_negative",
	"posting_permission",
)


class PostingError(frappe.ValidationError):
	"""The posting is not allowed: wrong code, closed folio, bad amount, or missing permission."""


class NoChargeCodeError(PostingError):
	"""No charge code covers the Item, so the posting service can't classify it."""


class FolioClosedError(PostingError):
	"""The folio no longer takes postings."""


class CheckOutBalanceError(frappe.ValidationError):
	"""A folio of the stay still has a balance, so the guest can't check out without an override."""


# --------------------------------------------------------------------------- folios


def create_folio(
	owner_type: str,
	owner_reference: str,
	*,
	label: str | None = None,
	payee_customer: str | None = None,
	payee_guest_profile: str | None = None,
	is_default: bool = False,
):
	"""Open a folio for a stay (or, later, a booking) and return it."""
	if owner_type == STAY:
		stay = _row(STAY, owner_reference, ["name", "property", "hotel_booking", "currency"])
		property_name, booking, currency = stay.property, stay.hotel_booking, stay.currency
	elif owner_type == BOOKING:
		booking_row = _row(BOOKING, owner_reference, ["name", "property", "currency"])
		property_name, booking, currency = booking_row.property, booking_row.name, booking_row.currency
		stay = None
	else:
		frappe.throw(_("A folio can't belong to a {0}.").format(_(owner_type)))
	if not property_name:
		frappe.throw(
			_("{0} {1} does not exist.").format(_(owner_type), owner_reference), frappe.DoesNotExistError
		)

	if not (payee_customer or payee_guest_profile):
		payee_customer, payee_guest_profile = default_payee(booking, stay.name if stay else None)
	window = frappe.db.count(FOLIO, {"owner_type": owner_type, "owner_reference": owner_reference}) + 1
	doc = frappe.get_doc(
		{
			"doctype": FOLIO,
			"property": property_name,
			"folio_label": label or (_(DEFAULT_FOLIO_LABEL) if is_default else _("Folio {0}").format(window)),
			"status": OPEN,
			"owner_type": owner_type,
			"owner_reference": owner_reference,
			"stay_reservation": stay.name if stay else None,
			"hotel_booking": booking,
			"window_number": window,
			"is_default": cint(is_default),
			"payee_customer": payee_customer,
			"payee_guest_profile": payee_guest_profile,
			"payee_name": _payee_name(payee_customer, payee_guest_profile),
			"currency": currency or frappe.db.get_value("Hotel Property", property_name, "currency"),
		}
	)
	doc.flags[SERVICE_FLAG] = True
	doc.insert(ignore_permissions=True)
	log_event(
		FOLIO,
		doc.name,
		"Folio Opened",
		to_status=OPEN,
		data={"owner": f"{owner_type} {owner_reference}", "payee": doc.payee_name},
		property_name=property_name,
	)
	return doc


def default_payee(booking: str, stay: str | None) -> tuple[str | None, str | None]:
	"""(Customer, Guest Profile) to bill: the booking's Customer, else the stay's lead guest.

	A guest without a Customer is still a valid payee: settlement (F11) creates or reuses one for
	the guest at invoicing time (decision D-3).
	"""
	customer = frappe.db.get_value(BOOKING, booking, "booker_customer")
	if customer:
		return customer, None
	guest = frappe.db.get_value(STAY, stay, "lead_guest") if stay else None
	if not guest:
		return None, None
	return frappe.db.get_value("Guest Profile", guest, "customer"), guest


def _payee_name(customer: str | None, guest_profile: str | None) -> str | None:
	if guest_profile:
		return frappe.db.get_value("Guest Profile", guest_profile, "full_name")
	if customer:
		return frappe.db.get_value("Customer", customer, "customer_name")
	return None


def ensure_default_folio(stay_name: str) -> str:
	"""The stay's default folio, created on first call. Safe to call again."""
	existing = frappe.db.get_value(STAY, stay_name, "default_folio")
	if existing:
		return existing
	folio = create_folio(STAY, stay_name, is_default=True)
	frappe.db.set_value(STAY, stay_name, "default_folio", folio.name, update_modified=False)
	refresh_pending(folio.name)
	return folio.name


def stay_folios(stay_name: str, statuses=None) -> list[str]:
	filters = {"stay_reservation": stay_name}
	if statuses:
		filters["status"] = ["in", list(statuses)]
	return frappe.get_all(FOLIO, filters=filters, pluck="name", order_by="window_number asc, creation asc")


LOCKED_FOLIO_FIELDS = (
	"name",
	"property",
	"status",
	"currency",
	"stay_reservation",
	"hotel_booking",
	"posted_debits",
	"posted_credits",
	"balance",
	"transaction_count",
)


def lock_folio(folio_name: str) -> frappe._dict:
	"""Lock the folio row and return it as it is now.

	This is a locking read, so it sees changes committed while it waited for the lock. A plain
	read could return the transaction's older snapshot (REPEATABLE READ), and totals built on it
	would overwrite another request's posting.
	"""
	try:
		row = frappe.db.get_value(FOLIO, folio_name, LOCKED_FOLIO_FIELDS, as_dict=True, for_update=True)
	except frappe.QueryDeadlockError as error:
		raise InventoryConflictError(
			_("Folio {0} changed while this request was running. Please try again.").format(folio_name)
		) from error
	if not row:
		frappe.throw(_("Guest Folio {0} does not exist.").format(folio_name), frappe.DoesNotExistError)
	return row


# --------------------------------------------------------------------------- charge codes


def resolve_charge_code(item: str) -> frappe._dict:
	"""The Revenue code an Item posts with: fixed Item first, then the nearest covering Item Group."""
	fixed = frappe.db.get_value(
		CHARGE_CODE,
		{"item": item, "transaction_type": REVENUE, "is_active": 1},
		CODE_FIELDS,
		as_dict=True,
	)
	if fixed:
		return fixed
	item_group = frappe.db.get_value("Item", item, "item_group")
	if not item_group:
		frappe.throw(_("Item {0} does not exist.").format(item), frappe.DoesNotExistError)

	code = frappe.qb.DocType(CHARGE_CODE)
	group = frappe.qb.DocType("Item Group")
	target = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=True)
	covering = (
		frappe.qb.from_(code)
		.join(group)
		.on(group.name == code.item_group)
		.select(code.name)
		.where(code.transaction_type == REVENUE)
		.where(code.is_active == 1)
		.where(code.item.isnull() | (code.item == ""))
		.where(group.lft <= target.lft)
		.where(group.rgt >= target.rgt)
		# The deepest covering group is the nearest one.
		.orderby(group.lft, order=Order.desc)
		.limit(1)
	).run(pluck=True)
	if not covering:
		frappe.throw(
			_(
				"No charge code covers Item {0} (Item Group {1}). Ask a manager to add a Revenue charge code for that group."
			).format(item, item_group),
			NoChargeCodeError,
		)
	return _code(covering[0])


def search_postable_items(text: str = "", limit: int = 20) -> list[dict]:
	"""Sales Items a Revenue charge code covers, so staff are only offered what they can post."""
	code = frappe.qb.DocType(CHARGE_CODE)
	group = frappe.qb.DocType("Item Group")
	ranges = (
		frappe.qb.from_(code)
		.join(group)
		.on(group.name == code.item_group)
		.select(group.lft, group.rgt)
		.where(code.transaction_type == REVENUE)
		.where(code.is_active == 1)
		.where(code.item.isnull() | (code.item == ""))
	).run(as_dict=True)
	fixed = frappe.get_all(
		CHARGE_CODE,
		filters={"transaction_type": REVENUE, "is_active": 1, "item": ["is", "set"]},
		pluck="item",
	)
	covered_groups = []
	if ranges:
		condition = None
		for row in ranges:
			inside = (group.lft >= row.lft) & (group.rgt <= row.rgt)
			condition = inside if condition is None else condition | inside
		covered_groups = frappe.qb.from_(group).select(group.name).where(condition).run(pluck=True)
	if not covered_groups and not fixed:
		return []

	item = frappe.qb.DocType("Item")
	coverage = None
	if covered_groups:
		coverage = item.item_group.isin(covered_groups)
	if fixed:
		coverage = item.name.isin(fixed) if coverage is None else coverage | item.name.isin(fixed)
	query = (
		frappe.qb.from_(item)
		.select(item.name, item.item_name, item.item_group, item.standard_rate)
		.where(item.disabled == 0)
		.where(item.is_sales_item == 1)
		.where(item.has_variants == 0)
		.where(coverage)
		.orderby(item.item_name)
		.limit(max(1, min(cint(limit) or 20, 50)))
	)
	text = (text or "").strip()
	if text:
		pattern = f"%{text}%"
		query = query.where(item.name.like(pattern) | item.item_name.like(pattern))
	return query.run(as_dict=True)


def _code(name: str) -> frappe._dict:
	row = _row(CHARGE_CODE, name, CODE_FIELDS)
	if not row:
		frappe.throw(_("Charge Code {0} does not exist.").format(name), frappe.DoesNotExistError)
	return row


# --------------------------------------------------------------------------- posting


def post(
	folio: str,
	charge_code: str,
	amount,
	*,
	posting_key: str,
	direction: str | None = None,
	quantity=1,
	unit_rate=None,
	tax_amount=0,
	item: str | None = None,
	description: str | None = None,
	business_date=None,
	service_date=None,
	source_doctype: str | None = None,
	source_name: str | None = None,
	source_line: str | None = None,
	stay_guest: str | None = None,
	reverses: str | None = None,
	reason: str | None = None,
	approved_by: str | None = None,
	notes: str | None = None,
	is_manual: bool = False,
) -> dict:
	"""Post one transaction to `folio`, exactly once per `posting_key`.

	`amount` is the gross amount, always positive; `direction` (Debit or Credit) defaults to the
	code's natural direction. Returns {"name", "created"}: `created` is False when the key was
	already posted, and the existing transaction is returned unchanged.
	"""
	posting_key = (posting_key or "").strip()
	if not posting_key or len(posting_key) > POSTING_KEY_LENGTH:
		frappe.throw(
			_("A posting needs a key of 1 to {0} characters.").format(POSTING_KEY_LENGTH), PostingError
		)

	folio_doc = lock_folio(folio)
	# A fast path for retries, so a repeated request after the folio closed still returns its
	# posting. The unique index on posting_key, below, is what guarantees exactly once.
	existing = _posted(posting_key)
	if existing:
		return {"name": existing, "created": False}

	if folio_doc.status not in POSTABLE_STATUSES:
		frappe.throw(
			_("Folio {0} is {1} and takes no more postings.").format(folio_doc.name, _(folio_doc.status)),
			FolioClosedError,
		)
	code = _code(charge_code)
	if not code.is_active:
		frappe.throw(_("Charge Code {0} is inactive.").format(code.name), PostingError)

	direction = _direction(code, direction, is_reversal=bool(reverses))
	currency = folio_doc.currency
	gross_minor = to_minor(amount, currency)
	tax_minor = to_minor(tax_amount, currency)
	if gross_minor <= 0:
		frappe.throw(_("The amount must be more than zero."), PostingError)
	if tax_minor < 0 or tax_minor > gross_minor:
		frappe.throw(_("The tax can't be negative or more than the amount."), PostingError)
	quantity = flt(quantity) or 1
	if quantity <= 0:
		frappe.throw(_("The quantity must be more than zero."), PostingError)

	item = _posting_item(code, item, is_reversal=bool(reverses))
	item_row = (
		_row("Item", item, ["item_name", "item_group"])
		if item
		else frappe._dict(item_name=None, item_group=None)
	)
	business_date = getdate(business_date or _business_date(folio_doc.property))
	guest = _stay_guest(folio_doc, stay_guest)
	room = _room_snapshot(folio_doc.stay_reservation)

	gross = from_minor(gross_minor, currency)
	doc = frappe.get_doc(
		{
			"doctype": TRANSACTION,
			"docstatus": 1,
			"property": folio_doc.property,
			"guest_folio": folio_doc.name,
			"stay_reservation": folio_doc.stay_reservation,
			"hotel_booking": folio_doc.hotel_booking,
			"direction": direction,
			"transaction_type": code.transaction_type,
			"charge_code": code.name,
			"reverses": reverses,
			"item": item,
			"item_group": item_row.item_group or code.item_group,
			"description_snapshot": (description or item_row.item_name or code.description)[:140],
			"print_group": code.print_group,
			"is_room_revenue": code.is_room_revenue,
			"accounting_mode": code.accounting_mode,
			"is_manual": cint(is_manual),
			"quantity": quantity,
			"unit_rate": flt(unit_rate)
			if unit_rate is not None
			else from_minor(round(gross_minor / quantity), currency),
			"net_amount": from_minor(gross_minor - tax_minor, currency),
			"tax_amount": from_minor(tax_minor, currency),
			"gross_amount": gross,
			"currency": currency,
			"exchange_rate": 1,
			"base_gross_amount": gross,
			"business_date": business_date,
			"service_date": getdate(service_date or business_date),
			"posting_datetime": now_datetime(),
			"posting_key": posting_key,
			"source_doctype": source_doctype,
			"source_name": source_name,
			"source_line": source_line,
			"stay_guest": guest.name,
			"consumer_guest_profile": guest.guest_profile,
			"room_occupancy": room.occupancy,
			"room_number_snapshot": room.room_number,
			"reason": (reason or "").strip() or None,
			"approved_by": approved_by,
			"notes": notes,
		}
	)
	doc.flags[SERVICE_FLAG] = True

	messages = len(frappe.local.message_log)
	frappe.db.savepoint(SAVEPOINT)
	try:
		doc.insert(ignore_permissions=True)
	except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
		# Another request posted this key after our fast-path read. Return its transaction.
		frappe.db.rollback(save_point=SAVEPOINT)
		del frappe.local.message_log[messages:]
		existing = _posted(posting_key, lock=True)
		if not existing:
			raise
		return {"name": existing, "created": False}

	_add_to_totals(folio_doc, direction, gross_minor)
	log_event(
		FOLIO,
		folio_doc.name,
		"Transaction Reversed" if reverses else f"{direction} Posted",
		data={
			"transaction": doc.name,
			"posting_key": posting_key,
			"charge_code": code.name,
			"item": item,
			"amount": gross,
			"reverses": reverses,
		},
		reason=doc.reason,
		property_name=folio_doc.property,
		business_date=business_date,
	)
	return {"name": doc.name, "created": True}


def _posted(posting_key: str, lock: bool = False) -> str | None:
	"""The transaction posted under this key, if any.

	The fast path reads without a lock: a locking read of a missing key takes a gap lock, and two
	postings to different folios could then deadlock on their inserts. After a duplicate-key error
	the row exists, so `lock=True` takes only a record lock, and it sees the other request's
	commit, which a plain read inside an older snapshot can miss.
	"""
	return frappe.db.get_value(TRANSACTION, {"posting_key": posting_key}, "name", for_update=lock)


def _direction(code, direction: str | None, is_reversal: bool) -> str:
	natural = NATURAL_DIRECTION.get(code.transaction_type)
	if not direction:
		if not natural:
			frappe.throw(
				_("{0} postings need a direction: Debit or Credit.").format(_(code.transaction_type)),
				PostingError,
			)
		return natural
	if direction not in OPPOSITE:
		frappe.throw(_("Direction must be Debit or Credit."), PostingError)
	if natural and direction != natural and not is_reversal and not code.allow_negative:
		# Posting a code against its direction (a negative charge) is a discount in disguise.
		frappe.throw(
			_("Charge Code {0} doesn't allow negative postings. Reverse the transaction instead.").format(
				code.name
			),
			PostingError,
		)
	return direction


def _posting_item(code, item: str | None, is_reversal: bool) -> str | None:
	"""The Item the invoice will bill: the one picked, or the code's fixed Item."""
	if not item:
		item = code.item
	if code.transaction_type in ITEM_TYPES and not item:
		frappe.throw(
			_("Charge Code {0} covers a group: pick the Item to post.").format(code.name), PostingError
		)
	if not item or is_reversal:
		return item
	if code.item and item != code.item:
		frappe.throw(_("Charge Code {0} posts only Item {1}.").format(code.name, code.item), PostingError)
	item_row = _row("Item", item, ["item_group", "disabled", "is_sales_item"])
	if not item_row:
		frappe.throw(_("Item {0} does not exist.").format(item), frappe.DoesNotExistError)
	if item_row.disabled or not item_row.is_sales_item:
		frappe.throw(_("Item {0} is disabled or not a sales item.").format(item), PostingError)
	if code.item_group and not is_in_group(item_row.item_group, code.item_group):
		frappe.throw(
			_("Item {0} is not in Item Group {1}, which Charge Code {2} covers.").format(
				item, code.item_group, code.name
			),
			PostingError,
		)
	return item


def _stay_guest(folio_doc, stay_guest: str | None) -> frappe._dict:
	if not stay_guest:
		return frappe._dict(name=None, guest_profile=None)
	guest = _row(STAY_GUEST, stay_guest, ["name", "stay_reservation", "guest_profile"])
	if not guest or guest.stay_reservation != folio_doc.stay_reservation:
		frappe.throw(_("Guest {0} is not part of this folio's stay.").format(stay_guest), PostingError)
	return guest


def _room_snapshot(stay_name: str | None) -> frappe._dict:
	"""The stay's occupancy and the room it is in now, copied onto the line for its history."""
	if not stay_name:
		return frappe._dict(occupancy=None, room_number=None)
	from frappoint.vuna_hospitality.services.front_desk import current_assignment

	occupancy = frappe.db.get_value(STAY, stay_name, "room_occupancy")
	assignment = current_assignment(occupancy) if occupancy else None
	return frappe._dict(occupancy=occupancy, room_number=assignment.room_number if assignment else None)


def _business_date(property_name: str):
	return frappe.db.get_value("Hotel Property", property_name, "business_date")


def _add_to_totals(folio_doc, direction: str, gross_minor: int) -> None:
	"""Add one posting to the cached totals in SQL, so the totals never depend on a stale read."""
	amount = from_minor(gross_minor, folio_doc.currency)
	debit, credit = (amount, 0) if direction == DEBIT else (0, amount)
	table = frappe.qb.DocType(FOLIO)
	(
		frappe.qb.update(table)
		.set(table.posted_debits, table.posted_debits + debit)
		.set(table.posted_credits, table.posted_credits + credit)
		.set(table.balance, table.balance + debit - credit)
		.set(table.transaction_count, table.transaction_count + 1)
		.set(table.modified, now_datetime())
		.where(table.name == folio_doc.name)
	).run()


def _set_totals(folio_name: str, currency: str, debits: int, credits: int, count: int) -> None:
	frappe.db.set_value(
		FOLIO,
		folio_name,
		{
			"posted_debits": from_minor(debits, currency),
			"posted_credits": from_minor(credits, currency),
			"balance": from_minor(debits - credits, currency),
			"transaction_count": count,
		},
	)


# --------------------------------------------------------------------------- manual posting and reversal


def post_manual_charge(
	folio: str,
	item: str,
	*,
	quantity=1,
	rate=None,
	description: str | None = None,
	stay_guest: str | None = None,
	notes: str | None = None,
	request_id: str | None = None,
) -> dict:
	"""A front-desk charge: staff pick an Item; the code, income account, and tax follow from it.

	`request_id` makes a retried request (a double click, a lost response) post once. Without it,
	every call posts a new charge.
	"""
	code = resolve_charge_code(item)
	if not code.allow_manual_posting:
		frappe.throw(_("Charge Code {0} can't be posted by hand.").format(code.name), PostingError)
	if code.posting_permission and code.posting_permission not in frappe.get_roles():
		frappe.throw(
			_("Posting {0} needs the {1} role.").format(code.name, code.posting_permission),
			frappe.PermissionError,
		)
	property_name, currency = frappe.db.get_value(FOLIO, folio, ["property", "currency"])
	company = frappe.db.get_value("Hotel Property", property_name, "company")
	if not income_account(item, company):
		frappe.throw(_("Item {0} has no income account for {1}.").format(item, company), PostingError)

	quantity = flt(quantity) or 1
	unit_rate = flt(rate) if rate not in (None, "") else get_item_rate(item, property_name)
	if unit_rate <= 0:
		frappe.throw(_("Give a rate for Item {0}: it has no selling price.").format(item), PostingError)
	amount = from_minor(to_minor(Decimal(str(unit_rate)) * Decimal(str(quantity)), currency), currency)
	key = f"manual:{folio}:{(request_id or '').strip() or frappe.generate_hash(length=16)}"
	return post(
		folio,
		code.name,
		amount,
		posting_key=key,
		quantity=quantity,
		unit_rate=unit_rate,
		item=item,
		description=description,
		stay_guest=stay_guest,
		notes=notes,
		is_manual=True,
	)


def get_item_rate(item: str, property_name: str) -> float:
	"""The Item's selling price in the property's currency, from the default selling price list."""
	currency = frappe.db.get_value("Hotel Property", property_name, "currency")
	price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
	if price_list:
		rate = frappe.db.get_value(
			"Item Price",
			{
				"item_code": item,
				"price_list": price_list,
				"currency": currency,
				"selling": 1,
				"customer": ["is", "not set"],
			},
			"price_list_rate",
		)
		if rate:
			return flt(rate)
	return flt(frappe.db.get_value("Item", item, "standard_rate"))


def reverse_transaction(transaction: str, reason: str, notes: str | None = None) -> dict:
	"""Cancel out a posted transaction with an equal one in the opposite direction.

	The original stays as it was. Reversing the same transaction twice returns the first reversal.
	"""
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for the reversal."), PostingError)
	original = _row(
		TRANSACTION,
		transaction,
		[
			"name",
			"docstatus",
			"guest_folio",
			"charge_code",
			"direction",
			"gross_amount",
			"tax_amount",
			"quantity",
			"unit_rate",
			"item",
			"description_snapshot",
			"service_date",
			"stay_guest",
			"reverses",
		],
	)
	if not original or original.docstatus != 1:
		frappe.throw(_("Folio Transaction {0} does not exist.").format(transaction), frappe.DoesNotExistError)
	if original.reverses:
		frappe.throw(
			_("{0} is itself a reversal. Post the charge again instead of reversing it.").format(
				original.name
			),
			PostingError,
		)
	return post(
		original.guest_folio,
		original.charge_code,
		original.gross_amount,
		posting_key=f"rev:{original.name}",
		direction=OPPOSITE[original.direction],
		quantity=original.quantity,
		unit_rate=original.unit_rate,
		tax_amount=original.tax_amount,
		item=original.item,
		description=_("Reversal: {0}").format(original.description_snapshot),
		# The correction posts today; the guest still received the service on the original date.
		service_date=original.service_date,
		stay_guest=original.stay_guest,
		reverses=original.name,
		reason=reason,
		approved_by=frappe.session.user,
		notes=notes,
		is_manual=True,
	)


# --------------------------------------------------------------------------- balances


def rebuild_folio_balance(folio: str) -> dict:
	"""Recompute the folio's cached totals from its transactions. Reports any drift it fixed."""
	folio_doc = lock_folio(folio)
	currency = folio_doc.currency
	rows = _locked_lines(folio, "direction", "gross_amount")
	debits = sum(to_minor(row.gross_amount, currency) for row in rows if row.direction == DEBIT)
	credits = sum(to_minor(row.gross_amount, currency) for row in rows if row.direction == CREDIT)
	before = {
		"posted_debits": flt(folio_doc.posted_debits),
		"posted_credits": flt(folio_doc.posted_credits),
		"balance": flt(folio_doc.balance),
		"transaction_count": cint(folio_doc.transaction_count),
	}
	after = {
		"posted_debits": from_minor(debits, currency),
		"posted_credits": from_minor(credits, currency),
		"balance": from_minor(debits - credits, currency),
		"transaction_count": len(rows),
	}
	drift = before != after
	if drift:
		_set_totals(folio, currency, debits, credits, len(rows))
		log_event(FOLIO, folio, "Balance Rebuilt", data={"before": before, "after": after})
	refresh_pending(folio)
	return {"folio": folio, "before": before, "after": after, "drift": drift}


def _locked_lines(folio: str, *fields: str) -> list:
	"""The folio's posted lines, read with a lock so lines committed meanwhile are included."""
	table = frappe.qb.DocType(TRANSACTION)
	return (
		frappe.qb.from_(table)
		.select(*(table[field] for field in fields))
		.where(table.guest_folio == folio)
		.where(table.docstatus == 1)
		.for_update()
	).run(as_dict=True)


def refresh_pending(folio: str) -> None:
	"""Nights not posted yet, shown beside the balance (§15.7). Only the default folio has them
	until routing (F12) can send room charges elsewhere."""
	row = _row(FOLIO, folio, ["stay_reservation", "is_default", "currency"])
	pending = 0
	if row.stay_reservation and row.is_default:
		totals = frappe.get_all(
			RATE_NIGHT,
			filters={"stay_reservation": row.stay_reservation, "posting_state": "Pending"},
			pluck="total",
		)
		pending = sum(to_minor(total, row.currency) for total in totals)
	frappe.db.set_value(
		FOLIO, folio, "pending_total", from_minor(pending, row.currency), update_modified=False
	)


def refresh_stay_pending(stay_name: str) -> None:
	for folio in stay_folios(stay_name):
		refresh_pending(folio)


def has_billable_activity(folio: str) -> bool:
	"""True if the folio holds a transaction that isn't cancelled out by a reversal."""
	rows = _locked_lines(folio, "name", "reverses")
	reversed_names = {row.reverses for row in rows if row.reverses}
	return any(not row.reverses and row.name not in reversed_names for row in rows)


def close_idle_folios(stay_name: str, reason: str | None = None) -> list[str]:
	"""Close the stay's open folios that have nothing to invoice. The others wait for settlement."""
	closed = []
	for name in stay_folios(stay_name, POSTABLE_STATUSES):
		row = lock_folio(name)
		if to_minor(row.balance, row.currency) or has_billable_activity(name):
			continue
		transition(
			frappe.get_doc(FOLIO, name),
			CLOSED,
			reason=reason,
			updates={"closed_at": now_datetime(), "closed_by": frappe.session.user, "pending_total": 0},
			event_type="Folio Closed",
			ignore_permissions=True,
		)
		closed.append(name)
	return closed


# --------------------------------------------------------------------------- check-out


def assert_folios_settled(stay, override_reason: str | None = None) -> None:
	"""Check-out needs every open folio of the stay at zero (F6 rule, enforced from F7).

	A Front Desk Manager may check the guest out anyway with a reason; the balances stay open for
	settlement (F11) and the override is audited.
	"""
	owing = []
	for name in stay_folios(stay.name, POSTABLE_STATUSES):
		row = lock_folio(name)
		if to_minor(row.balance, row.currency):
			row.folio_label = frappe.db.get_value(FOLIO, name, "folio_label")
			owing.append(row)
	if not owing:
		return

	summary = ", ".join(
		_("{0} ({1}): {2}").format(
			row.folio_label,
			row.name,
			frappe.format(row.balance, {"fieldtype": "Currency", "options": row.currency}),
		)
		for row in owing
	)
	override_reason = (override_reason or "").strip()
	if not override_reason:
		frappe.throw(
			_(
				"Settle the folio balance before check-out, or ask a Front Desk Manager to override: {0}."
			).format(summary),
			CheckOutBalanceError,
		)
	if not set(FOLIO_MANAGER_ROLES) & set(frappe.get_roles()):
		frappe.throw(
			_("Only a Front Desk Manager can check out a guest who still owes money."), frappe.PermissionError
		)
	log_event(
		STAY,
		stay.name,
		"Check-out Balance Override",
		reason=override_reason,
		data={"folios": {row.name: row.balance for row in owing}},
	)


# --------------------------------------------------------------------------- views


TRANSACTION_FIELDS = [
	"name",
	"direction",
	"transaction_type",
	"charge_code",
	"item",
	"description_snapshot",
	"print_group",
	"quantity",
	"unit_rate",
	"net_amount",
	"tax_amount",
	"gross_amount",
	"business_date",
	"service_date",
	"posting_datetime",
	"posting_key",
	"consumer_guest_profile",
	"room_number_snapshot",
	"reverses",
	"reason",
	"is_manual",
	"owner",
]


def folio_details(folio: str) -> dict:
	"""One folio with its posted lines, newest last, and which of them are reversed."""
	doc = frappe.get_doc(FOLIO, folio)
	summary = doc.as_dict(no_default_fields=True)
	summary["name"] = doc.name
	transactions = frappe.get_all(
		TRANSACTION,
		filters={"guest_folio": folio, "docstatus": 1},
		fields=TRANSACTION_FIELDS,
		order_by="posting_datetime asc, creation asc",
	)
	reversed_by = {row.reverses: row.name for row in transactions if row.reverses}
	guests = {
		row.name: row.full_name
		for row in frappe.get_all(
			"Guest Profile",
			filters={"name": ["in", list({row.consumer_guest_profile for row in transactions} - {None})]},
			fields=["name", "full_name"],
		)
	}
	for row in transactions:
		row["reversed_by"] = reversed_by.get(row.name)
		row["consumer_name"] = guests.get(row.consumer_guest_profile)
	return {"folio": summary, "transactions": transactions}


def stay_folio_details(stay_name: str) -> dict:
	"""The Folio Workspace: every folio of the stay, the pending nights, and combined totals."""
	stay = _row(
		STAY,
		stay_name,
		["name", "property", "status", "lead_guest_name", "currency", "default_folio", "hotel_booking"],
	)
	folios = [folio_details(name) for name in stay_folios(stay_name)]
	nights = frappe.get_all(
		RATE_NIGHT,
		filters={"stay_reservation": stay_name, "posting_state": "Pending"},
		fields=["night_date", "total"],
		order_by="night_date asc",
	)
	currency = stay.currency
	guests = frappe.get_all(
		STAY_GUEST,
		filters={"stay_reservation": stay_name, "status": ["not in", ["Removed"]]},
		fields=["name", "guest_name", "role"],
		order_by="creation asc",
	)
	return {
		"stay": stay,
		"business_date": _business_date(stay.property),
		"folios": folios,
		"pending_nights": nights,
		"guests": guests,
		"totals": {
			"balance": from_minor(
				sum(to_minor(entry["folio"]["balance"], currency) for entry in folios), currency
			),
			"pending": from_minor(sum(to_minor(night.total, currency) for night in nights), currency),
		},
	}
