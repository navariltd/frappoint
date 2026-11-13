"""Charge routing: which folio an automatic charge posts to (design §15.6; feature F12).

From highest to lowest precedence:

1. An explicit destination: a charge staff post to a folio they chose, a transfer, a payment.
   These never consult the rules.
2. A guest- or service-specific rule (Release 2).
3. A stay-level **Charge Routing Rule**: "room charges go to the company's folio".
4. A company, group, or travel-agent template copied to the booking (Release 2).
5. The stay's default folio.

Night audit (room nights, package components, levies) and policy fees resolve their folio here.
Within tier 3 the most specific rule wins: a charge code over an item group, an item group over
room charges, room charges over all charges. Two rules of the same rank that send a charge to
different folios stop the posting until staff remove one, so a charge never lands on a folio
by chance. A rule whose folio is already settled or closed is skipped.
"""

import frappe
from frappe import _

from frappoint.vuna_hospitality.services import folio
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.money import to_minor
from frappoint.vuna_hospitality.services.reservations import STAY, _row

RULE = "Charge Routing Rule"
SERVICE_FLAG = "from_routing_service"

ALL_CHARGES = "All Charges"
ROOM_CHARGES = "Room Charges"
ITEM_GROUP = "Item Group"
CHARGE_CODE = "Charge Code"
# A higher rank is more specific and wins.
RANK = {ALL_CHARGES: 1, ROOM_CHARGES: 2, ITEM_GROUP: 3, CHARGE_CODE: 4}
CLOSED_STAY_STATUSES = ("Checked Out", "Cancelled", "Expired", "No Show")


class RoutingError(frappe.ValidationError):
	pass


class RoutingConflictError(RoutingError):
	"""Two equally specific rules send the same charge to different folios."""


# --------------------------------------------------------------------------- rules


def add_rule(
	stay_name: str,
	target_folio: str,
	route: str,
	*,
	charge_code: str | None = None,
	item_group: str | None = None,
	notes: str | None = None,
) -> str:
	"""Send the stay's `route` charges to `target_folio` from now on. Returns the rule.

	Adding the same rule again returns the existing one. Charges already posted don't move; move
	them with a transfer.
	"""
	stay = _row(STAY, stay_name, ["name", "property", "hotel_booking", "status"])
	if not stay:
		frappe.throw(_("Stay Reservation {0} does not exist.").format(stay_name), frappe.DoesNotExistError)
	if stay.status in CLOSED_STAY_STATUSES:
		frappe.throw(_("Stay {0} is {1}.").format(stay.name, _(stay.status)), RoutingError)
	if route not in RANK:
		frappe.throw(_("Choose which charges to send: {0}.").format(", ".join(RANK)), RoutingError)
	charge_code = charge_code if route == CHARGE_CODE else None
	item_group = item_group if route == ITEM_GROUP else None
	if route == CHARGE_CODE:
		code = _row(folio.CHARGE_CODE, charge_code, ["transaction_type", "is_active"])
		if not code or code.transaction_type != folio.REVENUE:
			frappe.throw(_("Choose a Revenue charge code to send."), RoutingError)
	if route == ITEM_GROUP and not frappe.db.exists("Item Group", item_group):
		frappe.throw(_("Choose the item group to send."), RoutingError)

	target = _row(
		folio.FOLIO, target_folio, ["name", "stay_reservation", "hotel_booking", "status", "folio_label"]
	)
	if not target or target.stay_reservation != stay.name:
		frappe.throw(_("Send charges to a folio of this stay."), RoutingError)
	if target.status not in folio.POSTABLE_STATUSES:
		frappe.throw(_("Folio {0} is {1}.").format(target.name, _(target.status)), RoutingError)

	same = {
		"stay_reservation": stay.name,
		"route": route,
		"is_active": 1,
		"charge_code": charge_code,
		"item_group": item_group,
	}
	existing = frappe.get_all(RULE, filters=same, fields=["name", "target_folio"])
	for row in existing:
		if row.target_folio == target.name:
			return row.name
	if existing:
		frappe.throw(
			_("{0} already go to folio {1}. Remove that rule first.").format(
				_describe(route, charge_code, item_group), existing[0].target_folio
			),
			RoutingConflictError,
		)

	doc = frappe.get_doc(
		{
			"doctype": RULE,
			"property": stay.property,
			"stay_reservation": stay.name,
			"hotel_booking": stay.hotel_booking,
			"route": route,
			"charge_code": charge_code,
			"item_group": item_group,
			"target_folio": target.name,
			"target_label": target.folio_label,
			"is_active": 1,
			"notes": (notes or "").strip() or None,
		}
	)
	doc.flags[SERVICE_FLAG] = True
	doc.insert(ignore_permissions=True)
	log_event(
		STAY,
		stay.name,
		"Routing Rule Added",
		data={"rule": doc.name, "charges": _describe(route, charge_code, item_group), "folio": target.name},
	)
	folio.refresh_stay_pending(stay.name)
	return doc.name


def remove_rule(rule: str, reason: str) -> None:
	"""Stop the rule. Charges it already routed stay where they are."""
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for removing the routing rule."), RoutingError)
	doc = frappe.get_doc(RULE, rule)
	if not doc.is_active:
		return
	doc.update({"is_active": 0, "removed_reason": reason})
	doc.flags[SERVICE_FLAG] = True
	doc.save(ignore_permissions=True)
	log_event(
		STAY,
		doc.stay_reservation,
		"Routing Rule Removed",
		reason=reason,
		data={"rule": doc.name, "charges": _describe(doc.route, doc.charge_code, doc.item_group)},
	)
	folio.refresh_stay_pending(doc.stay_reservation)


def _describe(route: str, charge_code: str | None, item_group: str | None) -> str:
	if route == CHARGE_CODE:
		return _("{0} charges").format(charge_code)
	if route == ITEM_GROUP:
		return _("{0} charges").format(item_group)
	return _(route)


def stay_rules(stay_name: str) -> list:
	"""The stay's active rules, most specific first, with the folio each sends to."""
	rules = frappe.get_all(
		RULE,
		filters={"stay_reservation": stay_name, "is_active": 1},
		fields=[
			"name",
			"route",
			"charge_code",
			"item_group",
			"target_folio",
			"target_label",
			"notes",
			"creation",
		],
		order_by="creation asc",
	)
	for row in rules:
		row["rank"] = RANK[row.route]
		row["description"] = _describe(row.route, row.charge_code, row.item_group)
		row["target_status"] = frappe.db.get_value(folio.FOLIO, row.target_folio, "status")
	return sorted(rules, key=lambda row: -row["rank"])


# --------------------------------------------------------------------------- resolution


def destination(
	stay_name: str, charge_code: str, default: str | None = None, rules=None, codes: dict | None = None
) -> str:
	"""The folio a charge with `charge_code` posts to: the most specific matching rule's, else
	`default` (the stay's default folio). To resolve many charges of one stay, pass `rules` (from
	`stay_rules`) and one `codes` dict, so neither the rules nor the charge codes are read again."""
	default = (
		default
		or frappe.db.get_value(STAY, stay_name, "default_folio")
		or folio.ensure_default_folio(stay_name)
	)
	rules = stay_rules(stay_name) if rules is None else rules
	if not rules:
		return default
	code = _code_facts(charge_code, {} if codes is None else codes)
	if code.transaction_type != folio.REVENUE:
		return default

	best_rank, targets = 0, set()
	for rule in rules:
		if rule["target_status"] not in folio.POSTABLE_STATUSES or not _matches(rule, code):
			continue
		if rule["rank"] > best_rank:
			best_rank, targets = rule["rank"], {rule["target_folio"]}
		elif rule["rank"] == best_rank:
			targets.add(rule["target_folio"])
	if not targets:
		return default
	if len(targets) > 1:
		frappe.throw(
			_(
				"Charges with code {0} match routing rules to more than one folio ({1}). Remove one of them."
			).format(charge_code, ", ".join(sorted(targets))),
			RoutingConflictError,
		)
	return targets.pop()


def _code_facts(charge_code: str, cache: dict) -> frappe._dict:
	if charge_code not in cache:
		code = _row(
			folio.CHARGE_CODE,
			charge_code,
			["name", "transaction_type", "is_room_revenue", "item", "item_group"],
		)
		group = code.item_group or (code.item and frappe.db.get_value("Item", code.item, "item_group"))
		code["groups"] = set(_ancestors(group)) if group else set()
		cache[charge_code] = code
	return cache[charge_code]


def _ancestors(item_group: str) -> list[str]:
	"""The group and every group above it, so a rule on "Food" catches "Beverages" under it."""
	lft, rgt = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"]) or (None, None)
	if lft is None:
		return [item_group]
	return frappe.get_all("Item Group", filters={"lft": ["<=", lft], "rgt": [">=", rgt]}, pluck="name")


def _matches(rule, code) -> bool:
	if rule["route"] == ALL_CHARGES:
		return True
	if rule["route"] == ROOM_CHARGES:
		return bool(code.is_room_revenue)
	if rule["route"] == ITEM_GROUP:
		return rule["item_group"] in code.groups
	return rule["charge_code"] == code.name


# --------------------------------------------------------------------------- pending nights


def pending_by_folio(stay_name: str) -> dict[str, int]:
	"""Minor units of the stay's unposted nights, per folio they will post to."""
	stay = _row(STAY, stay_name, ["name", "default_folio", "rate_plan", "currency"])
	if not stay.default_folio:
		return {}
	nights = frappe.get_all(
		"Stay Rate Night",
		filters={"stay_reservation": stay_name, "posting_state": "Pending"},
		fields=["total", "components"],
	)
	if not nights:
		return {}
	rules = stay_rules(stay_name)
	codes: dict = {}
	room_code = None
	totals: dict[str, int] = {}
	for night in nights:
		components = frappe.parse_json(night.components) if night.components else None
		if not components:
			room_code = room_code or frappe.db.get_value("Rate Plan", stay.rate_plan, "room_charge_code")
			components = [{"charge_code": room_code, "amount": night.total}]
		for component in components:
			target = (
				destination(stay_name, component["charge_code"], stay.default_folio, rules, codes)
				if rules
				else stay.default_folio
			)
			totals[target] = totals.get(target, 0) + to_minor(component["amount"], stay.currency)
	return totals
