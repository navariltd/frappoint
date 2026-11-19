"""What has to be settled before night audit closes the day (design §21.1; plan F19).

Each check lists what it found. **Blocking** checks stop the audit until the problem is fixed or
someone allowed to overrides it with a reason; **warnings** are shown and recorded but never stop
it.

| Check | Severity | Override |
|---|---|---|
| Arrivals not checked in | Blocking | Night audit roles: they become no-shows tonight. |
| Departures not checked out | Blocking | Night audit roles and the Front Desk Manager: they stay in house, with no charge for the extra night. |
| Open cashier shifts | Blocking | Front Desk Manager (decision D-9). |
| Posting exceptions | Blocking | Front Desk Manager: failed service charges, and earlier nights still unposted. |
| Reconciliation differences | Blocking (raised by the Reconcile stage) | Hospitality Manager or Hotel Accountant. |
| Room discrepancies | Warning | |
| Folios in Settlement Pending | Warning | |

Overrides are kept on the run with the user, the role they used, and the reason.
"""

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

from frappoint.vuna_hospitality.constants import (
	FOLIO_MANAGER_ROLES,
	FRONT_DESK_MANAGER,
	HOSPITALITY_MANAGER,
	HOTEL_ACCOUNTANT,
	NIGHT_AUDIT_ROLES,
)

BLOCKING = "Blocking"
WARNING = "Warning"

ARRIVALS = "arrivals"
DEPARTURES = "departures"
OPEN_SHIFTS = "open_shifts"
POSTING_EXCEPTIONS = "posting_exceptions"
RECONCILIATION = "reconciliation"
ROOM_DISCREPANCIES = "room_discrepancies"
SETTLEMENT_PENDING = "settlement_pending"

STAY = "Stay Reservation"
LISTED = 20

ARRIVAL_STATUSES = ("Confirmed", "Due In")
IN_HOUSE_STATUSES = ("In House", "Due Out")

# Who may let each blocking check pass, and what passing it means.
OVERRIDES = {
	ARRIVALS: (
		NIGHT_AUDIT_ROLES,
		"They are marked No Show tonight, with the no-show fee their policy sets.",
	),
	DEPARTURES: (
		(*NIGHT_AUDIT_ROLES, FRONT_DESK_MANAGER),
		"They stay in house. Their extra night is not charged until someone extends or checks them out.",
	),
	OPEN_SHIFTS: (
		FOLIO_MANAGER_ROLES,
		"The shifts stay open. Payments taken in them still count towards tonight's totals.",
	),
	POSTING_EXCEPTIONS: (
		FOLIO_MANAGER_ROLES,
		"The failed charges stay failed and are listed in tonight's report for follow-up.",
	),
	RECONCILIATION: (
		("System Manager", HOSPITALITY_MANAGER, HOTEL_ACCOUNTANT),
		"The differences are kept in tonight's report; the business date moves on.",
	),
}

TITLES = {
	ARRIVALS: "Arrivals not checked in",
	DEPARTURES: "Departures not checked out",
	OPEN_SHIFTS: "Open cashier shifts",
	POSTING_EXCEPTIONS: "Posting exceptions",
	RECONCILIATION: "Reconciliation differences",
	ROOM_DISCREPANCIES: "Room discrepancies",
	SETTLEMENT_PENDING: "Folios in Settlement Pending",
}

HINTS = {
	ARRIVALS: "Check them in, cancel them, or let the audit mark them No Show.",
	DEPARTURES: "Check them out or extend their stay.",
	OPEN_SHIFTS: "Close the shifts from the Cashier page.",
	POSTING_EXCEPTIONS: "Retry or release the failed service charges; check out or post the missed nights.",
	RECONCILIATION: "Investigate the differences, then run the audit again.",
	ROOM_DISCREPANCIES: "Housekeeping and the front desk disagree about these rooms.",
	SETTLEMENT_PENDING: "Their invoices failed to submit. Settle them again from the folio.",
}


def _check(key: str, severity: str, items: list[dict]) -> dict:
	roles, consequence = OVERRIDES.get(key, ((), None))
	return {
		"key": key,
		"title": _(TITLES[key]),
		"hint": _(HINTS[key]),
		"severity": severity,
		"count": len(items),
		"items": items[:LISTED],
		"override_roles": list(roles),
		"override_consequence": _(consequence) if consequence else None,
		"can_override": bool(set(roles) & set(frappe.get_roles())),
	}


def _stays(filters: dict) -> list[dict]:
	return [
		{"name": row.name, "label": row.lead_guest_name or row.name, "doctype": STAY}
		for row in frappe.get_all(
			STAY, filters=filters, fields=["name", "lead_guest_name"], order_by="name asc"
		)
	]


def arrivals(property_name: str, business_date) -> list[dict]:
	return _stays(
		{
			"property": property_name,
			"status": ["in", ARRIVAL_STATUSES],
			"arrival_date": ["<=", getdate(business_date)],
		}
	)


def departures(property_name: str, business_date) -> list[dict]:
	return _stays(
		{
			"property": property_name,
			"status": ["in", IN_HOUSE_STATUSES],
			"departure_date": ["<=", getdate(business_date)],
		}
	)


def open_shifts(property_name: str, business_date) -> list[dict]:
	return [
		{"name": row.name, "label": row.cashier, "doctype": "Cashier Shift"}
		for row in frappe.get_all(
			"Cashier Shift",
			filters={
				"property": property_name,
				"status": "Open",
				"business_date": ["<=", getdate(business_date)],
			},
			fields=["name", "cashier"],
			order_by="opened_at asc",
		)
	]


def posting_exceptions(property_name: str, business_date) -> list[dict]:
	"""Service charges that failed to post, and in-house nights before tonight still unposted."""
	items = [
		{
			"name": row.name,
			"label": _("{0}: {1}").format(row.guest_name or row.name, row.posting_error or _("not posted")),
			"doctype": "Service Participant",
		}
		for row in frappe.get_all(
			"Service Participant",
			filters={"property": property_name, "status": "Failed"},
			fields=["name", "guest_name", "posting_error"],
			order_by="creation asc",
		)
	]
	night = frappe.qb.DocType("Stay Rate Night")
	stay = frappe.qb.DocType(STAY)
	missed = (
		frappe.qb.from_(night)
		.join(stay)
		.on(stay.name == night.stay_reservation)
		.select(night.name, night.night_date, stay.name.as_("stay"), stay.lead_guest_name)
		.where(night.property == property_name)
		.where(night.posting_state == "Pending")
		.where(night.night_date < getdate(business_date))
		.where(stay.status.isin(IN_HOUSE_STATUSES))
		.orderby(night.night_date)
	).run(as_dict=True)
	items += [
		{
			"name": row.stay,
			"label": _("{0}: night of {1} not posted").format(
				row.lead_guest_name or row.stay, frappe.format(row.night_date, "Date")
			),
			"doctype": STAY,
		}
		for row in missed
	]
	return items


def room_discrepancies(property_name: str, business_date) -> list[dict]:
	from frappoint.vuna_hospitality.services import housekeeping

	return [
		{
			"name": row.get("hotel_room") or row.get("room"),
			"label": _("Room {0}: {1}").format(row.get("room_number"), row.get("kind") or ""),
			"doctype": "Hotel Room",
		}
		for row in housekeeping.discrepancies(property_name, business_date)
	]


def settlement_pending(property_name: str, business_date=None) -> list[dict]:
	return [
		{
			"name": row.name,
			"label": _("{0}: {1}").format(row.payee_name or row.name, row.settlement_error or ""),
			"doctype": "Guest Folio",
		}
		for row in frappe.get_all(
			"Guest Folio",
			filters={"property": property_name, "status": "Settlement Pending"},
			fields=["name", "payee_name", "settlement_error"],
			order_by="modified asc",
		)
	]


CHECKS = (
	(ARRIVALS, BLOCKING, arrivals),
	(DEPARTURES, BLOCKING, departures),
	(OPEN_SHIFTS, BLOCKING, open_shifts),
	(POSTING_EXCEPTIONS, BLOCKING, posting_exceptions),
	(ROOM_DISCREPANCIES, WARNING, room_discrepancies),
	(SETTLEMENT_PENDING, WARNING, settlement_pending),
)


def precheck(property_name: str, business_date) -> list[dict]:
	"""Every pre-check for the property's day, blocking ones first."""
	return [_check(key, severity, finder(property_name, business_date)) for key, severity, finder in CHECKS]


def blocking(checks: list[dict], overrides: dict | None = None) -> list[dict]:
	"""Blocking checks that found something and have no override."""
	overrides = overrides or {}
	return [
		check
		for check in checks
		if check["severity"] == BLOCKING and check["count"] and not overrides.get(check["key"])
	]


def override_row(check: dict, reason: str) -> dict:
	"""The run's record of an override. Refuses a missing reason or a role that may not override."""
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_('Give the reason for letting "{0}" pass.').format(check["title"]))
	roles = [role for role in check["override_roles"] if role in frappe.get_roles()]
	if not roles:
		raise frappe.PermissionError(
			_('You are not allowed to let "{0}" pass. Ask: {1}.').format(
				check["title"], ", ".join(_(role) for role in check["override_roles"])
			)
		)
	return {
		"check_key": check["key"],
		"check_title": check["title"],
		"found": check["count"],
		"reason": reason,
		"overridden_by": frappe.session.user,
		"role": roles[0],
		"overridden_at": now_datetime(),
	}


def reconciliation_check(problems: list[dict]) -> dict:
	"""The Reconcile stage's findings in the same shape as a pre-check."""
	return _check(
		RECONCILIATION,
		BLOCKING,
		[{"name": row.get("name"), "label": row["label"], "doctype": row.get("doctype")} for row in problems],
	)
