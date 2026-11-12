"""Package allowances (design §10.5; feature F9).

A package component marked as an allowance (breakfast, a spa credit) is posted every night like
any other component: it is revenue the guest paid as part of the rate. Posting it also **grants**
that amount, which the guest can redeem until it expires:

- **Consume.** When an outlet charge posts to the stay's folio for an Item that the allowance's
  charge code covers, a credit on that code offsets it, up to what is left. The covered part nets
  to zero; only the excess is charged.
- **Expire.** Night audit expires what is left once the allowance's last valid day closes, and
  check-out expires everything left. The unused amount is reclassified, not refunded: a credit on
  the allowance code and an equal charge on the property's breakage code (or the room code), so the
  folio balance is unchanged and the revenue moves to breakage income.

Every movement is a Package Allowance Entry with a unique posting key, and every folio line it
causes is posted through `folio.post` with its own key, so retries never double a credit.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate

from frappoint.vuna_hospitality.doctype.charge_code.charge_code import is_in_group
from frappoint.vuna_hospitality.services import folio
from frappoint.vuna_hospitality.services.money import from_minor, to_minor
from frappoint.vuna_hospitality.services.reservations import STAY

ENTRY = "Package Allowance Entry"
GRANT, CONSUME, EXPIRE = "Grant", "Consume", "Expire"
ROOM_REVENUE = "Room Revenue"

# Set on entries created by this service; the DocType refuses inserts without it.
SERVICE_FLAG = "from_allowance_service"


class AllowanceError(frappe.ValidationError):
	"""An allowance can't be expired: the property has no breakage charge code."""


def _entry(values: dict) -> str:
	"""Insert a ledger entry once per posting key. Returns its name."""
	existing = frappe.db.get_value(ENTRY, {"posting_key": values["posting_key"]}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({"doctype": ENTRY, **values})
	doc.flags[SERVICE_FLAG] = True
	return doc.insert(ignore_permissions=True).name


def grant(stay_name: str, folio_name: str, night, component: dict, transaction: str) -> str:
	"""Record the allowance a night's package component gives the guest."""
	tx = frappe.db.get_value(folio.TRANSACTION, transaction, ["gross_amount", "property"], as_dict=True)
	allowance = component["allowance"]
	return _entry(
		{
			"property": tx.property,
			"stay_reservation": stay_name,
			"guest_folio": folio_name,
			"entry_type": GRANT,
			"component_name": component["label"],
			"revenue_charge_code": component["charge_code"],
			"allowance_charge_code": allowance["charge_code"],
			"breakage_rule": allowance["breakage_rule"],
			"amount": tx.gross_amount,
			"night_date": night.night_date,
			"expires_on": add_days(getdate(night.night_date), allowance["valid_days"]),
			"folio_transaction": transaction,
			"posting_key": f"alw-grant:{transaction}",
		}
	)


def open_grants(stay_name: str, *, on_date=None, expiring_by=None) -> list[frappe._dict]:
	"""The stay's grants with something left, oldest expiry first, each with its `remaining`."""
	filters = {"stay_reservation": stay_name, "entry_type": GRANT}
	if on_date is not None:
		filters["expires_on"] = [">=", getdate(on_date)]
	if expiring_by is not None:
		filters["expires_on"] = ["<=", getdate(expiring_by)]
	grants = frappe.get_all(
		ENTRY,
		filters=filters,
		fields=[
			"name",
			"property",
			"guest_folio",
			"component_name",
			"revenue_charge_code",
			"allowance_charge_code",
			"breakage_rule",
			"amount",
			"expires_on",
		],
		order_by="expires_on asc, creation asc",
	)
	if not grants:
		return []
	used = frappe.get_all(
		ENTRY,
		filters={"grant": ["in", [row.name for row in grants]], "entry_type": ["in", [CONSUME, EXPIRE]]},
		fields=["grant", "amount"],
	)
	currency = frappe.db.get_value("Hotel Property", grants[0].property, "currency")
	spent: dict[str, int] = {}
	for row in used:
		spent[row.grant] = spent.get(row.grant, 0) + to_minor(row.amount, currency)
	result = []
	for row in grants:
		remaining = to_minor(row.amount, currency) - spent.get(row.name, 0)
		if remaining > 0:
			row.remaining_minor = remaining
			row.currency = currency
			result.append(row)
	return result


def offset_charge(transaction: str) -> list[str]:
	"""Offset an outlet charge against the stay's allowances that cover its Item.

	Returns the credit transactions posted. Safe to call again for the same charge.
	"""
	tx = frappe.db.get_value(
		folio.TRANSACTION,
		transaction,
		[
			"name",
			"guest_folio",
			"stay_reservation",
			"direction",
			"transaction_type",
			"item",
			"item_group",
			"gross_amount",
			"currency",
			"business_date",
			"stay_guest",
			"reverses",
		],
		as_dict=True,
	)
	if not tx or not tx.stay_reservation or tx.reverses or tx.direction != folio.DEBIT:
		return []
	if tx.transaction_type != folio.REVENUE or not tx.item:
		return []
	to_cover = to_minor(tx.gross_amount, tx.currency)
	credits = []
	for row in open_grants(tx.stay_reservation, on_date=tx.business_date):
		if to_cover <= 0:
			break
		covered_group = frappe.db.get_value("Charge Code", row.allowance_charge_code, "item_group")
		if not covered_group or not is_in_group(tx.item_group, covered_group):
			continue
		cover = min(row.remaining_minor, to_cover)
		result = folio.post(
			tx.guest_folio,
			row.allowance_charge_code,
			from_minor(cover, tx.currency),
			posting_key=f"alw:{tx.name}:{row.name}",
			item=tx.item,
			tax_inclusive=True,
			description=_("{0} allowance").format(row.component_name),
			business_date=tx.business_date,
			source_doctype=ENTRY,
			source_name=row.name,
			stay_guest=tx.stay_guest,
		)
		_entry(
			{
				"property": row.property,
				"stay_reservation": tx.stay_reservation,
				"guest_folio": tx.guest_folio,
				"entry_type": CONSUME,
				"grant": row.name,
				"component_name": row.component_name,
				"revenue_charge_code": row.revenue_charge_code,
				"allowance_charge_code": row.allowance_charge_code,
				"amount": from_minor(cover, tx.currency),
				"folio_transaction": result["name"],
				"posting_key": f"alw-use:{tx.name}:{row.name}",
			}
		)
		credits.append(result["name"])
		to_cover -= cover
	return credits


def restore_for_reversal(original: str, reason: str) -> list[str]:
	"""A reversed outlet charge gives back the allowance it used: its offset credits are reversed
	too, and the ledger records the amount as available again."""
	offsets = frappe.get_all(
		folio.TRANSACTION,
		filters={"posting_key": ["like", f"alw:{original}:%"], "docstatus": 1},
		fields=["name", "source_name", "gross_amount", "stay_reservation", "guest_folio", "property"],
	)
	reversals = []
	for row in offsets:
		reversal = folio.reverse_transaction(row.name, reason)
		grant_row = frappe.db.get_value(
			ENTRY,
			row.source_name,
			["component_name", "revenue_charge_code", "allowance_charge_code"],
			as_dict=True,
		)
		_entry(
			{
				"property": row.property,
				"stay_reservation": row.stay_reservation,
				"guest_folio": row.guest_folio,
				"entry_type": CONSUME,
				"grant": row.source_name,
				"component_name": grant_row.component_name,
				"revenue_charge_code": grant_row.revenue_charge_code,
				"allowance_charge_code": grant_row.allowance_charge_code,
				"amount": -row.gross_amount,
				"folio_transaction": reversal["name"],
				"posting_key": f"alw-restore:{row.name}",
			}
		)
		reversals.append(reversal["name"])
	return reversals


def expire(stay_name: str, business_date, *, everything: bool = False) -> int:
	"""Move unused allowance to breakage. Night audit expires grants whose last valid day is
	`business_date`; check-out passes `everything`. Returns how many grants were expired."""
	grants = open_grants(stay_name, expiring_by=None if everything else business_date)
	if not grants:
		return 0
	stay = frappe.db.get_value(STAY, stay_name, ["property", "rate_plan"], as_dict=True)
	breakage_code = frappe.db.get_value("Hotel Property", stay.property, "breakage_charge_code")
	room_code = frappe.db.get_value("Rate Plan", stay.rate_plan, "room_charge_code")
	for row in grants:
		amount = from_minor(row.remaining_minor, row.currency)
		target = room_code if row.breakage_rule == ROOM_REVENUE else breakage_code
		if not target:
			frappe.throw(
				_("Set a Breakage Charge Code on Hotel Property {0} to expire unused allowances.").format(
					stay.property
				),
				AllowanceError,
			)
		revenue_item = frappe.db.get_value("Charge Code", row.revenue_charge_code, "item")
		common = {
			"business_date": business_date,
			"source_doctype": ENTRY,
			"source_name": row.name,
			"tax_inclusive": True,
		}
		credit = folio.post(
			row.guest_folio,
			row.allowance_charge_code,
			amount,
			posting_key=f"exp:{row.name}:out",
			item=revenue_item,
			description=_("Unused {0}").format(row.component_name),
			**common,
		)
		folio.post(
			row.guest_folio,
			target,
			amount,
			posting_key=f"exp:{row.name}:in",
			description=_("Unused {0} (breakage)").format(row.component_name),
			**common,
		)
		_entry(
			{
				"property": row.property,
				"stay_reservation": stay_name,
				"guest_folio": row.guest_folio,
				"entry_type": EXPIRE,
				"grant": row.name,
				"component_name": row.component_name,
				"revenue_charge_code": row.revenue_charge_code,
				"allowance_charge_code": row.allowance_charge_code,
				"breakage_rule": row.breakage_rule,
				"amount": amount,
				"folio_transaction": credit["name"],
				"posting_key": f"alw-exp:{row.name}",
			}
		)
	return len(grants)
