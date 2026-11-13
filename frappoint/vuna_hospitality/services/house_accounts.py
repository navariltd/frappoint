"""House Accounts: folios with no room (design §15.10; feature F12).

A House Account is a named folio owner at a property: permanent (staff meals, a management
account) or for an event (a conference, a wedding), with dates. Its folio takes charges,
payments, and settlement exactly like a stay's, through the same services. It has no stay, no
Room Occupancy, and no inventory, so it never appears in occupancy statistics.

Each account has one current folio. Settling it closes that folio, and the account's next charge
opens a new one, so a permanent account is billed in periods (one invoice per settlement).
"""

import frappe
from frappe import _
from frappe.utils import getdate

from frappoint.vuna_hospitality.services import folio
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.reservations import _row
from frappoint.vuna_hospitality.services.status_commands import transition

ACCOUNT = "House Account"
ACTIVE, CLOSED = "Active", "Closed"
SERVICE_FLAG = "from_house_account_service"


class HouseAccountError(frappe.ValidationError):
	pass


def create(
	property_name: str,
	account_name: str,
	*,
	account_type: str = "Permanent",
	payee_customer: str | None = None,
	valid_from=None,
	valid_to=None,
	notes: str | None = None,
) -> str:
	account_name = (account_name or "").strip()
	if not account_name:
		frappe.throw(_("Name the house account."), HouseAccountError)
	if frappe.db.exists(ACCOUNT, {"property": property_name, "account_name": account_name, "status": ACTIVE}):
		frappe.throw(_("House account {0} already exists.").format(account_name), HouseAccountError)
	doc = frappe.get_doc(
		{
			"doctype": ACCOUNT,
			"property": property_name,
			"account_name": account_name,
			"account_type": account_type or "Permanent",
			"status": ACTIVE,
			"payee_customer": payee_customer or None,
			"valid_from": valid_from or None,
			"valid_to": valid_to or None,
			"notes": (notes or "").strip() or None,
		}
	)
	doc.insert(ignore_permissions=True)
	log_event(ACCOUNT, doc.name, "House Account Opened", to_status=ACTIVE, property_name=property_name)
	if account_type != "Event" or not valid_from or getdate(valid_from) <= _business_date(property_name):
		ensure_folio(doc.name)
	return doc.name


def _business_date(property_name: str):
	return getdate(frappe.db.get_value("Hotel Property", property_name, "business_date"))


def check_can_post(account_name: str) -> None:
	"""A closed account, or an event account outside its dates, takes no charges."""
	account = _row(ACCOUNT, account_name, ["status", "account_type", "valid_from", "valid_to", "property"])
	if account.status != ACTIVE:
		frappe.throw(_("House account {0} is closed.").format(account_name), HouseAccountError)
	if account.account_type != "Event":
		return
	business_date = _business_date(account.property)
	if account.valid_from and business_date < getdate(account.valid_from):
		frappe.throw(
			_("House account {0} opens on {1}.").format(
				account_name, frappe.format(account.valid_from, "Date")
			),
			HouseAccountError,
		)
	if account.valid_to and business_date > getdate(account.valid_to):
		frappe.throw(
			_("House account {0} ended on {1}.").format(
				account_name, frappe.format(account.valid_to, "Date")
			),
			HouseAccountError,
		)


def check_payee_change(doc) -> None:
	"""The payee can change until the current folio takes a payment, as for a stay's folio."""
	if not doc.current_folio:
		return
	from frappoint.vuna_hospitality.services.settlement import set_payee

	set_payee(doc.current_folio, doc.payee_customer, None)


def ensure_folio(account_name: str) -> str:
	"""The account's open folio, opening a new one if the last was settled or closed."""
	frappe.db.get_value(ACCOUNT, account_name, "name", for_update=True)
	doc = frappe.get_doc(ACCOUNT, account_name)
	check_can_post(doc.name)
	current = doc.current_folio and frappe.db.get_value(folio.FOLIO, doc.current_folio, "status")
	if current in folio.POSTABLE_STATUSES or current == "Settlement Pending":
		return doc.current_folio
	new = folio.create_folio(folio.HOUSE_ACCOUNT, doc.name, label=doc.account_name, is_default=True)
	doc.current_folio = new.name
	doc.flags[SERVICE_FLAG] = True
	doc.save(ignore_permissions=True)
	return new.name


def close(account_name: str, reason: str) -> None:
	"""Close the account. Its folios must be settled or empty first."""
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for closing the house account."), HouseAccountError)
	doc = frappe.get_doc(ACCOUNT, account_name)
	if doc.status == CLOSED:
		return
	for name in frappe.get_all(
		folio.FOLIO,
		filters={
			"house_account": doc.name,
			"status": ["in", [*folio.POSTABLE_STATUSES, "Settlement Pending"]],
		},
		pluck="name",
	):
		row = folio.lock_folio(name)
		if row.balance or folio.has_billable_activity(name):
			frappe.throw(
				_("Settle folio {0} before closing the house account.").format(name), HouseAccountError
			)
		transition(
			frappe.get_doc(folio.FOLIO, name),
			folio.CLOSED,
			reason=reason,
			updates={"closed_at": frappe.utils.now_datetime(), "closed_by": frappe.session.user},
			event_type="Folio Closed",
			ignore_permissions=True,
		)
	transition(doc, CLOSED, reason=reason, updates={"closed_reason": reason}, ignore_permissions=True)


def reopen(account_name: str, reason: str) -> None:
	doc = frappe.get_doc(ACCOUNT, account_name)
	if doc.status == ACTIVE:
		return
	transition(doc, ACTIVE, reason=reason, updates={"closed_reason": None}, ignore_permissions=True)


# --------------------------------------------------------------------------- views


def account_list(property_name: str) -> list[dict]:
	rows = frappe.get_all(
		ACCOUNT,
		filters={"property": property_name},
		fields=[
			"name",
			"account_name",
			"account_type",
			"status",
			"payee_customer",
			"valid_from",
			"valid_to",
			"current_folio",
		],
		order_by="status asc, account_name asc",
	)
	for row in rows:
		current = row.current_folio and _row(
			folio.FOLIO, row.current_folio, ["status", "balance", "currency"]
		)
		row["folio_status"] = current.status if current else None
		row["balance"] = current.balance if current else 0
		row["currency"] = (current.currency if current else None) or frappe.db.get_value(
			"Hotel Property", property_name, "currency"
		)
		row["payee_name"] = (
			frappe.db.get_value("Customer", row.payee_customer, "customer_name")
			if row.payee_customer
			else None
		)
	return rows


def account_folio_details(account_name: str) -> dict:
	"""The Folio Workspace for a House Account: the same shape as a stay's, without nights."""
	doc = frappe.get_doc(ACCOUNT, account_name)
	names = frappe.get_all(
		folio.FOLIO,
		filters={"house_account": doc.name},
		pluck="name",
		order_by="creation desc",
		limit=12,
	)
	folios = [folio.folio_details(name) for name in reversed(names)]
	currency = frappe.db.get_value("Hotel Property", doc.property, "currency")
	from frappoint.vuna_hospitality.services.money import from_minor, to_minor

	open_folios = [
		entry
		for entry in folios
		if entry["folio"]["status"] in (*folio.POSTABLE_STATUSES, "Settlement Pending")
	]
	return {
		"stay": {
			"name": doc.name,
			"property": doc.property,
			"status": doc.status,
			"lead_guest_name": doc.account_name,
			"currency": currency,
			"default_folio": doc.current_folio,
			"hotel_booking": None,
		},
		"house_account": {
			"name": doc.name,
			"account_name": doc.account_name,
			"account_type": doc.account_type,
			"status": doc.status,
			"payee_customer": doc.payee_customer,
			"valid_from": doc.valid_from,
			"valid_to": doc.valid_to,
			"current_folio": doc.current_folio,
		},
		"business_date": frappe.db.get_value("Hotel Property", doc.property, "business_date"),
		"folios": folios,
		"pending_nights": [],
		"guests": [],
		"totals": {
			"balance": from_minor(
				sum(to_minor(entry["folio"]["balance"], currency) for entry in open_folios), currency
			),
			"pending": 0,
		},
	}
