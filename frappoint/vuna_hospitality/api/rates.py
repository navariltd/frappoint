"""Rates and Restrictions endpoints (feature F13): the grid of nightly rates and restrictions for
one rate plan, bulk edits, resetting a derived plan's overrides, and regenerating derived rates.

Reading needs read access to Room Rate Day and the property. Changing rates or restrictions is for
Revenue Managers, Hospitality Managers and System Managers. Every change is audited.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate

from frappoint.vuna_hospitality.services import rates, restrictions
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.inventory import run_with_inventory_retry
from frappoint.vuna_hospitality.services.property_scope import assert_property_access

MAX_GRID_DAYS = 62
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _parse(value, default=None):
	if value in (None, ""):
		return default
	return json.loads(value) if isinstance(value, str) else value


def _check_plan(rate_plan: str, write: bool = False) -> frappe._dict:
	plan = frappe.db.get_value(
		"Rate Plan",
		rate_plan,
		[
			"name",
			"property",
			"rate_plan_name",
			"currency",
			"parent_rate_plan",
			"derivation_type",
			"derivation_value",
			"rounding_rule",
			"rounding_increment",
			"last_derived_on",
			"tax_inclusive",
		],
		as_dict=True,
	)
	if not plan:
		raise frappe.DoesNotExistError(_("Rate Plan {0} does not exist.").format(rate_plan))
	assert_property_access(plan.property)
	if write:
		frappe.only_for(restrictions.RATE_MANAGERS)
	frappe.has_permission("Room Rate Day", "read", throw=True)
	return plan


def _nights(from_date, to_date, weekdays=None) -> list:
	"""The nights from `from_date` to `to_date` inclusive, on the given weekdays (0 = Monday)."""
	start, end = getdate(from_date), getdate(to_date)
	if end < start:
		frappe.throw(_("The last night can't be before the first."))
	days = (end - start).days + 1
	if days > restrictions.MAX_BULK_NIGHTS:
		frappe.throw(_("Change at most {0} nights at once.").format(restrictions.MAX_BULK_NIGHTS))
	keep = {cint(day) for day in weekdays} if weekdays else set(range(7))
	return [add_days(start, offset) for offset in range(days) if add_days(start, offset).weekday() in keep]


def _derivation_text(plan) -> str | None:
	if not plan.parent_rate_plan:
		return None
	parent = frappe.db.get_value("Rate Plan", plan.parent_rate_plan, "rate_plan_name")
	value = flt(plan.derivation_value)
	change = (
		f"{value:+g}%"
		if plan.derivation_type != "Fixed Amount"
		else f"{'+' if value >= 0 else '-'}{frappe.format(abs(value), {'fieldtype': 'Currency', 'options': plan.currency})}"
	)
	rounding = (
		_(", rounded {0} to {1}").format(
			_(plan.rounding_rule).lower(), frappe.format(flt(plan.rounding_increment), {"fieldtype": "Float"})
		)
		if (plan.rounding_rule or "None") != "None"
		else ""
	)
	return _("{0} {1}{2}").format(parent, change, rounding)


@frappe.whitelist()
@require_hospitality
def get_rate_grid(
	property: str, rate_plan: str | None = None, start: str | None = None, days: int = 14
) -> dict:
	"""Rates and restrictions of one rate plan, per room type and night, for the grid page."""
	assert_property_access(property)
	frappe.has_permission("Room Rate Day", "read", throw=True)
	plans = frappe.get_all(
		"Rate Plan",
		filters={"property": property, "is_active": 1, "rate_basis": "Night"},
		fields=["name", "rate_plan_name", "parent_rate_plan"],
		order_by="rate_plan_name asc",
	)
	if not plans:
		return {"plans": [], "plan": None}
	rate_plan = rate_plan if any(row.name == rate_plan for row in plans) else plans[0].name
	plan = _check_plan(rate_plan)
	business_date = getdate(frappe.db.get_value("Hotel Property", property, "business_date"))
	first = getdate(start) if start else business_date
	days = max(1, min(cint(days) or 14, MAX_GRID_DAYS))
	dates = [add_days(first, offset) for offset in range(days)]
	room_types = frappe.get_all(
		"Room Type",
		filters={"property": property, "is_active": 1},
		fields=["name", "room_type_name", "code"],
		order_by="sort_order asc, room_type_name asc",
	)
	grid_rates: dict = {row.name: {} for row in room_types}
	for row in frappe.get_all(
		"Room Rate Day",
		filters={"rate_plan": rate_plan, "rate_date": ["between", [dates[0], dates[-1]]]},
		fields=["room_type", "rate_date", "rate", "source", "is_manual_override"],
	):
		if row.room_type in grid_rates:
			grid_rates[row.room_type][str(getdate(row.rate_date))] = {
				"rate": row.rate,
				"source": row.source,
				"manual": bool(row.is_manual_override),
			}
	grid_restrictions: dict = {}
	for room in room_types:
		cells = {}
		for night, row in restrictions.effective(property, rate_plan, room.name, dates).items():
			cells[str(night)] = {
				"name": row.name,
				"summary": restrictions.summary(row),
				"scope": _("this plan and room")
				if row.rate_plan and row.room_type
				else _("this plan")
				if row.rate_plan
				else _("this room, all plans")
				if row.room_type
				else _("all plans and rooms"),
				**{rule: row.get(rule) for rule in restrictions.RULES},
			}
		grid_restrictions[room.name] = cells
	return {
		"plans": [
			{"name": row.name, "label": row.rate_plan_name, "is_derived": bool(row.parent_rate_plan)}
			for row in plans
		],
		"plan": {
			"name": plan.name,
			"label": plan.rate_plan_name,
			"currency": plan.currency,
			"tax_inclusive": plan.tax_inclusive,
			"is_derived": bool(plan.parent_rate_plan),
			"parent": plan.parent_rate_plan,
			"derivation": _derivation_text(plan),
			"last_derived_on": plan.last_derived_on,
			"children": rates.child_plans(plan.name),
		},
		"business_date": business_date,
		"dates": [{"date": str(night), "weekday": WEEKDAYS[night.weekday()]} for night in dates],
		"room_types": room_types,
		"rates": grid_rates,
		"restrictions": grid_restrictions,
		"can_edit": bool(set(restrictions.RATE_MANAGERS) & set(frappe.get_roles())),
	}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def set_rates(
	rate_plan: str,
	room_types: str | list,
	from_date: str,
	to_date: str,
	weekdays: str | list | None = None,
	rate: float | None = None,
	adjust_percent: float | None = None,
	adjust_amount: float | None = None,
	reason: str | None = None,
) -> dict:
	"""Set, or adjust, the rate for each room type and night. On a derived plan this sets manual
	overrides; the plans derived from this one follow in the background."""
	_check_plan(rate_plan, write=True)
	nights = _nights(from_date, to_date, _parse(weekdays))
	return run_with_inventory_retry(
		lambda: rates.set_rates(
			rate_plan,
			_parse(room_types, []),
			nights,
			rate=rate,
			adjust_percent=adjust_percent,
			adjust_amount=adjust_amount,
			reason=reason,
		)
	)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def reset_rates(
	rate_plan: str, room_types: str | list, from_date: str, to_date: str, weekdays: str | list | None = None
) -> dict:
	"""Give hand-set nights on a derived plan back their derived rate."""
	_check_plan(rate_plan, write=True)
	nights = _nights(from_date, to_date, _parse(weekdays))
	return run_with_inventory_retry(lambda: rates.reset_to_derived(rate_plan, _parse(room_types, []), nights))


@frappe.whitelist(methods=["POST"])
@require_hospitality
def regenerate_rates(rate_plan: str) -> dict:
	"""Work out a derived plan's rates again from its parent, in the background."""
	plan = _check_plan(rate_plan, write=True)
	if not plan.parent_rate_plan:
		frappe.throw(_("Rate Plan {0} isn't derived from another plan.").format(rate_plan))
	rates.enqueue_regeneration(rate_plan)
	return {"queued": True}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def set_restrictions(
	property: str,
	from_date: str,
	to_date: str,
	weekdays: str | list | None = None,
	rate_plan: str | None = None,
	room_types: str | list | None = None,
	values: str | dict | None = None,
	clear: int = 0,
	notes: str | None = None,
) -> dict:
	"""Set or clear restrictions for the nights, for one plan (or all) and the room types (or all)."""
	assert_property_access(property)
	frappe.only_for(restrictions.RATE_MANAGERS)
	if rate_plan and frappe.db.get_value("Rate Plan", rate_plan, "property") != property:
		frappe.throw(_("Rate Plan {0} belongs to another property.").format(rate_plan))
	nights = _nights(from_date, to_date, _parse(weekdays))
	return run_with_inventory_retry(
		lambda: restrictions.set_restrictions(
			property,
			nights,
			rate_plans=[rate_plan or None],
			room_types=_parse(room_types) or [None],
			values=_parse(values, {}),
			clear=bool(cint(clear)),
			notes=notes,
		)
	)
