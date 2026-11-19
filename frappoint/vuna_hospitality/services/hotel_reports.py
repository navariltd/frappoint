"""Figures the hotel is run on, shared by night audit's stored report and the desk reports (§24).

One place computes each number, so the audit report and the Script Reports always agree.

Definitions:

- **Rooms available**: active rooms less those out of order that night. Out-of-service rooms are
  still sellable, so they count as available.
- **Rooms sold**: room nights posted for that night (Stay Rate Night Posted), plus complimentary
  nights (Waived, zero rate). Day use is not counted.
- **Occupancy %**: rooms sold (paid and complimentary) ÷ rooms available.
- **Room revenue**: net room revenue (before tax) posted for that service date, reversals
  subtracted.
- **ADR**: room revenue ÷ paid rooms sold (complimentary nights excluded).
- **RevPAR**: room revenue ÷ rooms available.

Amounts are in the property's currency and by business date, unless a report says otherwise.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate

from frappoint.vuna_hospitality.services.money import from_minor, to_minor

STAY = "Stay Reservation"
NIGHT = "Stay Rate Night"
TRANSACTION = "Folio Transaction"
FOLIO = "Guest Folio"
DEBIT, CREDIT = "Debit", "Credit"
IN_HOUSE_STATUSES = ("In House", "Due Out")
POSTABLE_FOLIO_STATUSES = ("Open", "Settlement Pending")
DEPOSIT_HELD_STATUSES = ("Partly Paid", "Received")


def currency(property_name: str) -> str:
	return frappe.db.get_value("Hotel Property", property_name, "currency")


def dates(from_date, to_date) -> list:
	start, end = getdate(from_date), getdate(to_date)
	return [add_days(start, offset) for offset in range(max(date_diff(end, start), 0) + 1)]


def _signed(direction: str, amount) -> float:
	return flt(amount) if direction == DEBIT else -flt(amount)


# --------------------------------------------------------------------------- rooms


def rooms_available(property_name: str, from_date, to_date) -> dict:
	"""{date: rooms available}: active rooms less the rooms out of order that night."""
	physical = frappe.db.count("Hotel Room", {"property": property_name, "is_active": 1})
	periods = frappe.get_all(
		"Room State Period",
		filters={
			"property": property_name,
			"docstatus": 1,
			"state": "Out of Order",
			"from_date": ["<=", getdate(to_date)],
			"to_date": [">", getdate(from_date)],
		},
		fields=["room", "from_date", "to_date"],
	)
	result = {}
	for night in dates(from_date, to_date):
		closed = {row.room for row in periods if getdate(row.from_date) <= night < getdate(row.to_date)}
		result[night] = max(physical - len(closed), 0)
	return result


def rooms_sold(property_name: str, from_date, to_date) -> dict:
	"""{date: {"paid": n, "comp": n}} from the nights posted (or waived as complimentary)."""
	result = defaultdict(lambda: {"paid": 0, "comp": 0})
	for row in frappe.get_all(
		NIGHT,
		filters={
			"property": property_name,
			"night_date": ["between", [getdate(from_date), getdate(to_date)]],
			"posting_state": ["in", ("Posted", "Waived")],
		},
		fields=["night_date", "posting_state"],
	):
		result[getdate(row.night_date)]["paid" if row.posting_state == "Posted" else "comp"] += 1
	return result


def room_revenue(property_name: str, from_date, to_date) -> dict:
	"""{service date: net room revenue}, reversals subtracted."""
	result = defaultdict(float)
	for row in frappe.get_all(
		TRANSACTION,
		filters={
			"property": property_name,
			"docstatus": 1,
			"is_room_revenue": 1,
			"service_date": ["between", [getdate(from_date), getdate(to_date)]],
		},
		fields=["service_date", "direction", "net_amount"],
	):
		result[getdate(row.service_date)] += _signed(row.direction, row.net_amount)
	return result


def occupancy(property_name: str, from_date, to_date) -> list[dict]:
	"""One row per night: rooms available and sold, occupancy %, room revenue, ADR and RevPAR."""
	money = currency(property_name)
	available = rooms_available(property_name, from_date, to_date)
	sold = rooms_sold(property_name, from_date, to_date)
	revenue = room_revenue(property_name, from_date, to_date)
	return [
		metrics(night, available[night], sold[night]["paid"], sold[night]["comp"], revenue[night], money)
		for night in dates(from_date, to_date)
	]


def metrics(night, available: int, paid: int, comp: int, revenue: float, money: str) -> dict:
	revenue = from_minor(to_minor(revenue, money), money)
	occupied = paid + comp
	return {
		"date": night,
		"rooms_available": available,
		"rooms_sold": occupied,
		"complimentary": comp,
		"occupancy": round(100 * occupied / available, 2) if available else 0,
		"room_revenue": revenue,
		"adr": round(revenue / paid, 2) if paid else 0,
		"revpar": round(revenue / available, 2) if available else 0,
		"currency": money,
	}


def total_metrics(rows: list[dict], money: str) -> dict:
	"""The same figures over a period, from its nightly rows."""
	available = sum(row["rooms_available"] for row in rows)
	comp = sum(row["complimentary"] for row in rows)
	paid = sum(row["rooms_sold"] for row in rows) - comp
	revenue = sum(flt(row["room_revenue"]) for row in rows)
	return metrics(None, available, paid, comp, revenue, money)


# --------------------------------------------------------------------------- money


def revenue_by_charge_code(property_name: str, from_date, to_date) -> list[dict]:
	"""Revenue posted per charge code by business date: net, tax and gross, reversals subtracted."""
	totals: dict[str, dict] = {}
	for row in frappe.get_all(
		TRANSACTION,
		filters={
			"property": property_name,
			"docstatus": 1,
			"transaction_type": "Revenue",
			"business_date": ["between", [getdate(from_date), getdate(to_date)]],
		},
		fields=["charge_code", "transaction_type", "direction", "net_amount", "tax_amount", "gross_amount"],
	):
		entry = totals.setdefault(
			row.charge_code,
			{"charge_code": row.charge_code, "lines": 0, "net": 0.0, "tax": 0.0, "gross": 0.0},
		)
		entry["lines"] += 1
		for field, source in (("net", "net_amount"), ("tax", "tax_amount"), ("gross", "gross_amount")):
			entry[field] += _signed(row.direction, row[source])
	descriptions = dict(
		frappe.get_all(
			"Charge Code",
			filters={"name": ["in", list(totals) or [""]]},
			fields=["name", "description"],
			as_list=True,
		)
	)
	rows = sorted(totals.values(), key=lambda row: -row["gross"])
	for row in rows:
		row["description"] = descriptions.get(row["charge_code"]) or row["charge_code"]
		for field in ("net", "tax", "gross"):
			row[field] = round(row[field], 2)
	return rows


def payments_by_charge_code(property_name: str, from_date, to_date) -> list[dict]:
	"""Money taken and refunded per payment charge code by business date. Refunds subtract."""
	totals: dict[str, dict] = {}
	for row in frappe.get_all(
		TRANSACTION,
		filters={
			"property": property_name,
			"docstatus": 1,
			"transaction_type": ["in", ("Payment", "Deposit")],
			"business_date": ["between", [getdate(from_date), getdate(to_date)]],
		},
		fields=["charge_code", "direction", "gross_amount"],
	):
		entry = totals.setdefault(
			row.charge_code, {"charge_code": row.charge_code, "lines": 0, "amount": 0.0}
		)
		entry["lines"] += 1
		entry["amount"] -= _signed(row.direction, row.gross_amount)
	return sorted(
		({**row, "amount": round(row["amount"], 2)} for row in totals.values()),
		key=lambda row: -row["amount"],
	)


def ledger_control(property_name: str) -> list[dict]:
	"""What every open folio holds, grouped: in house, departed, house accounts, settlement pending."""
	groups: dict[str, dict] = {}
	stays = {}
	folios = frappe.get_all(
		FOLIO,
		filters={"property": property_name, "status": ["in", POSTABLE_FOLIO_STATUSES]},
		fields=[
			"name",
			"status",
			"owner_type",
			"stay_reservation",
			"balance",
			"posted_debits",
			"posted_credits",
		],
	)
	stay_names = [row.stay_reservation for row in folios if row.stay_reservation]
	if stay_names:
		stays = dict(
			frappe.get_all(
				STAY, filters={"name": ["in", stay_names]}, fields=["name", "status"], as_list=True
			)
		)
	for row in folios:
		group = ledger_group(row, stays.get(row.stay_reservation))
		entry = groups.setdefault(
			group, {"group": group, "folios": 0, "debits": 0.0, "credits": 0.0, "balance": 0.0}
		)
		entry["folios"] += 1
		entry["debits"] += flt(row.posted_debits)
		entry["credits"] += flt(row.posted_credits)
		entry["balance"] += flt(row.balance)
	order = [_("In house"), _("Before arrival"), _("Departed"), _("House accounts"), _("Settlement pending")]
	return sorted(
		(
			{**row, **{key: round(row[key], 2) for key in ("debits", "credits", "balance")}}
			for row in groups.values()
		),
		key=lambda row: order.index(row["group"]) if row["group"] in order else len(order),
	)


def ledger_group(folio_row, stay_status: str | None) -> str:
	if folio_row.status == "Settlement Pending":
		return _("Settlement pending")
	if folio_row.owner_type == "House Account":
		return _("House accounts")
	if stay_status in IN_HOUSE_STATUSES:
		return _("In house")
	if stay_status in ("Held", "Confirmed", "Due In"):
		return _("Before arrival")
	return _("Departed")


def deposits_held(property_name: str) -> dict:
	"""Deposits received and not yet applied: how many, and how much is held."""
	from frappoint.vuna_hospitality.services import deposits

	money = currency(property_name)
	names = frappe.get_all(
		"Guest Deposit",
		filters={"property": property_name, "status": ["in", DEPOSIT_HELD_STATUSES]},
		pluck="name",
	)
	held = sum(deposits.amounts(name).held for name in names)
	return {"deposits": len(names), "held": from_minor(held, money)}


# --------------------------------------------------------------------------- front office


def movements(property_name: str, business_date) -> dict:
	"""How many guests arrived, left, stayed, didn't come, and cancelled on the business date."""
	day = getdate(business_date)
	base = {"property": property_name}
	return {
		"arrivals": frappe.db.count(
			STAY,
			{**base, "arrival_date": day, "status": ["in", (*IN_HOUSE_STATUSES, "Checked Out")]},
		),
		"departures": frappe.db.count(STAY, {**base, "departure_date": day, "status": "Checked Out"}),
		"in_house": frappe.db.count(
			NIGHT, {**base, "night_date": day, "posting_state": ["in", ("Posted", "Waived")]}
		),
		"no_shows": frappe.db.count(STAY, {**base, "arrival_date": day, "status": "No Show"}),
		# Cancellations by the calendar day they were made on.
		"cancellations": frappe.db.count(
			STAY, {**base, "status": "Cancelled", "cancelled_at": ["between", [day, add_days(day, 1)]]}
		),
	}


# --------------------------------------------------------------------------- desk reports


def report_scope(filters) -> tuple[str, object] | None:
	"""(property, its business date) for a report's filters, after checking access."""
	from frappoint.vuna_hospitality.services.property_scope import assert_property_access

	property_name = (filters or {}).get("property")
	if not property_name:
		return None
	assert_property_access(property_name)
	return property_name, getdate(frappe.db.get_value("Hotel Property", property_name, "business_date"))


def stay_rooms(stay_names) -> dict:
	"""{stay: room number} from each stay's latest room segment."""
	rows = frappe.get_all(
		"Room Assignment",
		filters={"stay_reservation": ["in", list(stay_names) or [""]], "status": ["!=", "Cancelled"]},
		fields=["stay_reservation", "room_number", "start_datetime"],
		order_by="start_datetime asc",
	)
	return {row.stay_reservation: row.room_number for row in rows}


def column(
	fieldname: str, label: str, fieldtype: str = "Data", width: int = 120, options: str | None = None
) -> dict:
	field = {"fieldname": fieldname, "label": _(label), "fieldtype": fieldtype, "width": width}
	if options:
		field["options"] = options
	return field
