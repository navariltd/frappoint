"""Stay restrictions (design §10.3, quote step 2 of §10.7; feature F13).

A **Rate Restriction Day** holds the rules for one night: for one rate plan or every plan, and one
room type or every type. For a given plan, room type and night the most specific row wins, whole:
plan and room type, then plan only, then room type only, then the property-wide row. Each
combination has one row, named after it, so two edits can't create rival rows.

Rules, checked against a stay (arrival, departure, and the business date it's booked on):

- **Closed**: no new stay may include the night.
- **Closed to arrival / departure**: no stay may arrive, or leave, on the date.
- **Minimum stay (arriving)** and **maximum stay**: on the arrival date's row.
- **Minimum stay (through)**: on any night of the stay.
- **Minimum / maximum days ahead**: the arrival date's lead time from the business date.

A broken rule doesn't make a stay impossible: Revenue Managers and Front Desk Managers may
override it on a reservation with a reason, which is recorded on the stay.
"""

from datetime import date

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, getdate

from frappoint.vuna_hospitality.constants import (
	FRONT_DESK_MANAGER,
	HOSPITALITY_MANAGER,
	REVENUE_MANAGER,
)
from frappoint.vuna_hospitality.services.event_log import log_event

RESTRICTION = "Rate Restriction Day"
ALL = "ALL"
FLAGS = ("closed", "closed_to_arrival", "closed_to_departure")
LIMITS = ("min_stay_arrival", "min_stay_through", "max_stay", "min_advance_days", "max_advance_days")
RULES = FLAGS + LIMITS
# Roles that may book a stay against a restriction, with a reason.
OVERRIDE_ROLES = ("System Manager", HOSPITALITY_MANAGER, REVENUE_MANAGER, FRONT_DESK_MANAGER)
# Roles that set restrictions and rates.
RATE_MANAGERS = ("System Manager", HOSPITALITY_MANAGER, REVENUE_MANAGER)
MAX_BULK_NIGHTS = 731

# Reasons a quote gives, as staff read them.
CLOSED = "Closed"
CLOSED_TO_ARRIVAL = "Closed to Arrival"
CLOSED_TO_DEPARTURE = "Closed to Departure"


class RestrictionError(frappe.ValidationError):
	pass


# --------------------------------------------------------------------------- naming


def _code(doctype: str, name: str | None, field: str) -> str:
	if not name:
		return ALL
	return frappe.db.get_value(doctype, name, field) or name


def row_name(property_name: str, rate_plan: str | None, room_type: str | None, night) -> str:
	"""One row per property, plan (or every plan), room type (or every type) and night."""
	plan = _code("Rate Plan", rate_plan, "rate_plan_code")
	room = _code("Room Type", room_type, "code")
	return f"{property_name}-{plan}-{room}-{getdate(night)}"


def summary(row) -> str:
	"""The rules of a row in a few words: "Closed · Min 3 arriving"."""
	parts = []
	if row.get("closed"):
		parts.append(_("Closed"))
	if row.get("closed_to_arrival"):
		parts.append(_("No arrivals"))
	if row.get("closed_to_departure"):
		parts.append(_("No departures"))
	if cint(row.get("min_stay_arrival")):
		parts.append(_("Min {0} arriving").format(cint(row.get("min_stay_arrival"))))
	if cint(row.get("min_stay_through")):
		parts.append(_("Min {0} through").format(cint(row.get("min_stay_through"))))
	if cint(row.get("max_stay")):
		parts.append(_("Max {0}").format(cint(row.get("max_stay"))))
	if cint(row.get("min_advance_days")):
		parts.append(_("Book {0}+ days ahead").format(cint(row.get("min_advance_days"))))
	if cint(row.get("max_advance_days")):
		parts.append(_("Book within {0} days").format(cint(row.get("max_advance_days"))))
	return " · ".join(parts)


def has_rules(row) -> bool:
	return any(cint(row.get(rule)) for rule in RULES)


# --------------------------------------------------------------------------- reading


def effective(property_name: str, rate_plan: str, room_type: str, nights: list[date]) -> dict:
	"""{night: row} with the most specific row for each night that has one."""
	if not nights:
		return {}
	rows = frappe.get_all(
		RESTRICTION,
		filters={
			"property": property_name,
			"restriction_date": ["between", [min(nights), max(nights)]],
		},
		fields=["name", "rate_plan", "room_type", "restriction_date", *RULES],
	)
	wanted = set(nights)
	best: dict = {}
	for row in rows:
		night = getdate(row.restriction_date)
		if night not in wanted:
			continue
		if row.rate_plan and row.rate_plan != rate_plan:
			continue
		if row.room_type and row.room_type != room_type:
			continue
		# Plan and type (3) beat plan only (2), which beats type only (1), which beats all (0).
		rank = (2 if row.rate_plan else 0) + (1 if row.room_type else 0)
		if night not in best or rank > best[night][0]:
			best[night] = (rank, row)
	return {night: row for night, (_rank, row) in best.items()}


def check(
	property_name: str,
	rate_plan: str,
	room_type: str,
	arrival,
	departure,
	*,
	business_date=None,
	amendment: bool = False,
) -> list[dict]:
	"""The rules the stay breaks: [{"rule", "night", "reason"}], empty when it's allowed.

	An `amendment` (an existing stay changing its dates) isn't checked for booking lead time.
	"""
	arrival, departure = getdate(arrival), getdate(departure)
	length = date_diff(departure, arrival)
	nights = [add_days(arrival, offset) for offset in range(length)]
	rows = effective(property_name, rate_plan, room_type, [*nights, departure])
	broken: list[dict] = []

	def add(rule: str, night, reason: str) -> None:
		broken.append({"rule": rule, "night": getdate(night), "reason": reason})

	for night in nights:
		row = rows.get(night)
		if not row:
			continue
		if row.closed:
			add("closed", night, CLOSED)
		if cint(row.min_stay_through) > length:
			add(
				"min_stay_through",
				night,
				_("Minimum Stay {0} Nights").format(cint(row.min_stay_through)),
			)

	first = rows.get(arrival)
	if first:
		if first.closed_to_arrival:
			add("closed_to_arrival", arrival, CLOSED_TO_ARRIVAL)
		if cint(first.min_stay_arrival) > length:
			add(
				"min_stay_arrival",
				arrival,
				_("Minimum Stay {0} Nights").format(cint(first.min_stay_arrival)),
			)
		if cint(first.max_stay) and length > cint(first.max_stay):
			add("max_stay", arrival, _("Maximum Stay {0} Nights").format(cint(first.max_stay)))
		if not amendment:
			today = getdate(
				business_date or frappe.db.get_value("Hotel Property", property_name, "business_date")
			)
			lead = date_diff(arrival, today)
			if cint(first.min_advance_days) and lead < cint(first.min_advance_days):
				add(
					"min_advance_days",
					arrival,
					_("Book {0} Days Ahead").format(cint(first.min_advance_days)),
				)
			if cint(first.max_advance_days) and lead > cint(first.max_advance_days):
				add(
					"max_advance_days",
					arrival,
					_("Book Within {0} Days").format(cint(first.max_advance_days)),
				)

	last = rows.get(departure)
	if last and last.closed_to_departure:
		add("closed_to_departure", departure, CLOSED_TO_DEPARTURE)

	# One entry per reason, at its first night.
	seen, unique = set(), []
	for item in broken:
		if item["reason"] not in seen:
			seen.add(item["reason"])
			unique.append(item)
	return unique


def can_override() -> bool:
	return bool(set(OVERRIDE_ROLES) & set(frappe.get_roles()))


def assert_override(reason: str | None) -> str:
	"""A restriction override needs one of OVERRIDE_ROLES and a reason. Returns the reason."""
	if not can_override():
		frappe.throw(
			_("Only a Revenue Manager or Front Desk Manager can book against a restriction."),
			frappe.PermissionError,
		)
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for overriding the restriction."), RestrictionError)
	return reason


def describe(broken: list[dict]) -> str:
	return ", ".join(f"{item['reason']} ({frappe.format(item['night'], 'Date')})" for item in broken)


# --------------------------------------------------------------------------- writing


def audit_change(doc, event_type: str) -> None:
	"""Every restriction change is audited, also those made one by one in the desk (§10.1)."""
	if doc.flags.get("in_bulk"):
		return
	log_event(
		"Hotel Property",
		doc.property,
		event_type,
		data={
			"restriction": doc.name,
			"date": str(doc.restriction_date),
			"rate_plan": doc.rate_plan or ALL,
			"room_type": doc.room_type or ALL,
			"rules": summary(doc),
		},
		property_name=doc.property,
	)


def set_restrictions(
	property_name: str,
	nights: list,
	*,
	rate_plans: list[str | None] | None = None,
	room_types: list[str | None] | None = None,
	values: dict | None = None,
	clear: bool = False,
	notes: str | None = None,
) -> dict:
	"""Set (or with `clear`, remove) restrictions for every night, plan and room type given.

	`rate_plans` and `room_types` default to [None]: every plan, every type. `values` holds only the
	rules to change; others on an existing row stay as they are. A row left with no rule is
	deleted. Returns {"created", "updated", "deleted"}.
	"""
	nights = sorted({getdate(night) for night in nights})
	if not nights:
		frappe.throw(_("Choose at least one night."), RestrictionError)
	if len(nights) > MAX_BULK_NIGHTS:
		frappe.throw(_("Change at most {0} nights at once.").format(MAX_BULK_NIGHTS), RestrictionError)
	values = {key: value for key, value in (values or {}).items() if key in RULES}
	if not clear and not values:
		frappe.throw(_("Choose a restriction to set."), RestrictionError)
	for key, value in values.items():
		values[key] = 1 if key in FLAGS and cint(value) else cint(value)
		if values[key] < 0:
			frappe.throw(_("{0} cannot be negative.").format(_(key.replace("_", " "))), RestrictionError)

	counts = {"created": 0, "updated": 0, "deleted": 0}
	for rate_plan in rate_plans or [None]:
		for room_type in room_types or [None]:
			for night in nights:
				name = row_name(property_name, rate_plan, room_type, night)
				exists = frappe.db.exists(RESTRICTION, name)
				if clear:
					if exists:
						_delete(name)
						counts["deleted"] += 1
					continue
				doc = (
					frappe.get_doc(RESTRICTION, name)
					if exists
					else frappe.get_doc(
						{
							"doctype": RESTRICTION,
							"property": property_name,
							"rate_plan": rate_plan,
							"room_type": room_type,
							"restriction_date": night,
						}
					)
				)
				doc.update(values)
				if (notes or "").strip():
					doc.notes = notes.strip()
				doc.flags.in_bulk = True
				if not has_rules(doc):
					if exists:
						_delete(name)
						counts["deleted"] += 1
					continue
				doc.save(ignore_permissions=True)
				counts["updated" if exists else "created"] += 1

	log_event(
		"Hotel Property",
		property_name,
		"Restrictions Cleared" if clear else "Restrictions Updated",
		reason=(notes or "").strip() or None,
		data={
			**counts,
			"from": str(nights[0]),
			"to": str(nights[-1]),
			"nights": len(nights),
			"rate_plans": [plan or ALL for plan in rate_plans or [None]],
			"room_types": [room or ALL for room in room_types or [None]],
			"values": values,
		},
		property_name=property_name,
	)
	return counts


def _delete(name: str) -> None:
	"""Remove a row as part of a bulk change, which is audited once for the whole change."""
	doc = frappe.get_doc(RESTRICTION, name)
	doc.flags.in_bulk = True
	doc.delete(ignore_permissions=True)
