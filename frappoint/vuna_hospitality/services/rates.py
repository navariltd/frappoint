"""Room rates (design §10.1-10.2; features F3 and F13).

Room Rate Day is the only place a price lives: one row per rate plan, room type and night. Seasons,
derived plans and bulk updates are tools that write Room Rate Days; nothing reads a season or a
parent plan at booking time.

**Derived plans** (F13). A plan with a parent takes each of the parent's nightly rates, adjusts it
by a percentage or a fixed amount, and rounds it (to the nearest, up or down to an increment).
Whenever the parent's rates change (a season, a bulk edit, a hand edit) or the derivation itself
changes, the derived plan is regenerated in the background, and so on down a chain of plans. A
rate edited by hand on a derived plan is a manual override: regeneration keeps it, and the grid
flags it, until someone resets it to the derived rate.
"""

from datetime import date
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, now_datetime

from frappoint.vuna_hospitality.constants import HOSPITALITY_MANAGER, REVENUE_MANAGER
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.property_scope import assert_property_access

RATE_DAY = "Room Rate Day"
WEEKDAY_FIELDS = (
	"weekend_monday",
	"weekend_tuesday",
	"weekend_wednesday",
	"weekend_thursday",
	"weekend_friday",
	"weekend_saturday",
	"weekend_sunday",
)
RATE_MANAGERS = ("System Manager", HOSPITALITY_MANAGER, REVENUE_MANAGER)
# Lets the rate service save Room Rate Days without them being marked as manual overrides.
SERVICE_FLAG = "from_rate_service"


def rate_day_name(rate_plan: str, room_type_code: str, night) -> str:
	return f"{rate_plan}-{room_type_code}-{getdate(night)}"


def get_rates(rate_plan: str, room_type: str, nights: list[date]) -> dict[date, float]:
	"""The rate for each night that has one. Missing nights are not sellable on this plan."""
	if not nights:
		return {}
	return {
		getdate(row.rate_date): flt(row.rate)
		for row in frappe.get_all(
			RATE_DAY,
			filters={
				"rate_plan": rate_plan,
				"room_type": room_type,
				"rate_date": ["between", [min(nights), max(nights)]],
			},
			fields=["rate_date", "rate"],
		)
		if getdate(row.rate_date) in set(nights)
	}


def season_nights(season) -> list[date]:
	start, end = getdate(season.from_date), getdate(season.to_date)
	return [add_days(start, offset) for offset in range((end - start).days + 1)]


def season_rate_for(season, row, night: date) -> float:
	is_weekend = bool(season.get(WEEKDAY_FIELDS[night.weekday()]))
	return flt(row.weekend_rate) if is_weekend and flt(row.weekend_rate) else flt(row.weekday_rate)


def generate_from_season(season_name: str, overwrite_manual: bool = False) -> dict:
	"""Write a Room Rate Day for every room type and night in the season.

	Existing season or derivation rates are updated; hand-edited rates (manual overrides) are left
	alone unless `overwrite_manual` is set. Returns counts of created, updated and skipped rows.
	"""
	season = frappe.get_doc("Rate Season", season_name)
	plan = frappe.db.get_value("Rate Plan", season.rate_plan, ["property", "currency"], as_dict=True)
	nights = season_nights(season)
	codes = dict(
		frappe.get_all(
			"Room Type",
			filters={"name": ["in", [row.room_type for row in season.rates]]},
			fields=["name", "code"],
			as_list=True,
		)
	)
	existing = {
		row.name: row
		for row in frappe.get_all(
			RATE_DAY,
			filters={
				"rate_plan": season.rate_plan,
				"room_type": ["in", list(codes)],
				"rate_date": ["between", [nights[0], nights[-1]]],
			},
			fields=["name", "rate", "is_manual_override"],
		)
	}

	now, user = now_datetime(), frappe.session.user
	to_insert, created, updated, skipped = [], 0, 0, 0
	for row in season.rates:
		for night in nights:
			name = rate_day_name(season.rate_plan, codes[row.room_type], night)
			rate = season_rate_for(season, row, night)
			current = existing.get(name)
			if current is None:
				to_insert.append(
					[
						name,
						user,
						user,
						now,
						now,
						0,
						0,
						plan.property,
						season.rate_plan,
						row.room_type,
						night,
						rate,
						plan.currency,
						"Season",
						0,
						season.name,
					]
				)
				created += 1
			elif current.is_manual_override and not overwrite_manual:
				skipped += 1
			elif flt(current.rate) != rate or current.is_manual_override:
				frappe.db.set_value(
					RATE_DAY,
					name,
					{"rate": rate, "source": "Season", "season": season.name, "is_manual_override": 0},
				)
				updated += 1

	if to_insert:
		frappe.db.bulk_insert(
			RATE_DAY,
			[
				"name",
				"owner",
				"modified_by",
				"creation",
				"modified",
				"docstatus",
				"idx",
				"property",
				"rate_plan",
				"room_type",
				"rate_date",
				"rate",
				"currency",
				"source",
				"is_manual_override",
				"season",
			],
			to_insert,
			ignore_duplicates=True,
		)

	season.db_set("last_generated_on", now)
	schedule_derivation([season.rate_plan])
	result = {"created": created, "updated": updated, "skipped_manual": skipped, "nights": len(nights)}
	log_event(
		"Rate Plan",
		season.rate_plan,
		"Rates Generated",
		reason=_("Season {0}, {1} to {2}").format(season.season_name, season.from_date, season.to_date),
		data={**result, "season": season.name, "overwrite_manual": bool(overwrite_manual)},
		property_name=plan.property,
	)
	return result


@frappe.whitelist()
@require_hospitality
def generate_season_rates(season: str, overwrite_manual: bool = False) -> dict:
	"""Desk action on Rate Season: write its Room Rate Days."""
	frappe.only_for(RATE_MANAGERS)
	assert_property_access(frappe.db.get_value("Rate Season", season, "property"))
	return generate_from_season(season, overwrite_manual=frappe.utils.sbool(overwrite_manual))


# --------------------------------------------------------------------------- derived plans (F13)

DERIVATION_FIELDS = (
	"parent_rate_plan",
	"derivation_type",
	"derivation_value",
	"rounding_rule",
	"rounding_increment",
)
ROUNDING = {"Nearest": ROUND_HALF_UP, "Up": ROUND_CEILING, "Down": ROUND_FLOOR}
MAX_CHAIN = 5


def derive_rate(parent_rate, plan) -> float:
	"""The derived plan's rate for a night the parent sells at `parent_rate`. Never below zero."""
	rate = Decimal(str(flt(parent_rate)))
	value = Decimal(str(flt(plan.derivation_value)))
	if plan.derivation_type == "Fixed Amount":
		rate += value
	else:
		rate = rate * (Decimal(100) + value) / Decimal(100)
	increment = Decimal(str(flt(plan.rounding_increment)))
	mode = ROUNDING.get(plan.rounding_rule or "None")
	if mode and increment > 0:
		rate = (rate / increment).quantize(Decimal(1), rounding=mode) * increment
	return float(max(rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), Decimal(0)))


def child_plans(rate_plan: str) -> list[str]:
	return frappe.get_all("Rate Plan", filters={"parent_rate_plan": rate_plan}, pluck="name")


def check_derivation(plan) -> None:
	"""A parent on the same property and currency, on a nightly basis, with no loop."""
	if not plan.parent_rate_plan:
		return
	if plan.parent_rate_plan == plan.name:
		frappe.throw(_("A rate plan can't be derived from itself."))
	parent = frappe.db.get_value(
		"Rate Plan", plan.parent_rate_plan, ["property", "currency", "rate_basis"], as_dict=True
	)
	if parent.property != plan.property:
		frappe.throw(_("Parent Rate Plan {0} belongs to another property.").format(plan.parent_rate_plan))
	if (parent.currency or "") != (plan.currency or ""):
		frappe.throw(_("A derived plan must use its parent's currency ({0}).").format(parent.currency))
	if parent.rate_basis != plan.rate_basis:
		frappe.throw(_("A derived plan must be priced the same way as its parent (per night or day use)."))
	if plan.derivation_type == "Percentage" and flt(plan.derivation_value) <= -100:
		frappe.throw(_("A percentage adjustment must be more than -100%."))
	if (plan.rounding_rule or "None") != "None" and flt(plan.rounding_increment) <= 0:
		frappe.throw(_("Give the amount to round to."))
	ancestor, depth = plan.parent_rate_plan, 0
	while ancestor:
		if ancestor == plan.name:
			frappe.throw(
				_("Rate Plan {0} would be derived from itself through {1}.").format(
					plan.name, plan.parent_rate_plan
				)
			)
		depth += 1
		if depth > MAX_CHAIN:
			frappe.throw(_("Rate plans can be derived at most {0} levels deep.").format(MAX_CHAIN))
		ancestor = frappe.db.get_value("Rate Plan", ancestor, "parent_rate_plan")


def schedule_derivation(rate_plans) -> None:
	"""Regenerate the plans derived from `rate_plans`, in the background after this commit."""
	for parent in set(rate_plans or []):
		for child in child_plans(parent):
			enqueue_regeneration(child)


def enqueue_regeneration(rate_plan: str) -> None:
	"""One job per derived plan: a second request while one is queued is dropped, because the
	queued job reads the parent's rates when it runs. Tests run it at once."""
	frappe.enqueue(
		"frappoint.vuna_hospitality.services.rates.regenerate_derived_job",
		queue="long",
		job_id=f"derive-rates-{rate_plan}",
		deduplicate=True,
		enqueue_after_commit=True,
		now=bool(frappe.flags.in_test),
		rate_plan=rate_plan,
	)


def regenerate_derived_job(rate_plan: str) -> dict:
	"""Background job: regenerate one derived plan (and, through it, the plans derived from it)."""
	result = regenerate_derived(rate_plan)
	if not frappe.flags.in_test:
		frappe.db.commit()  # nosemgrep
	return result


def regenerate_derived(rate_plan: str, from_date=None, overwrite_manual: bool = False) -> dict:
	"""Write the derived plan's Room Rate Days from its parent's, from `from_date` (default: the
	property's business date) on. Manual overrides are kept unless `overwrite_manual`. A derived
	night whose parent night has no rate any more is removed, unless it was set by hand.
	"""
	plan = frappe.get_doc("Rate Plan", rate_plan)
	if not plan.parent_rate_plan:
		return {"created": 0, "updated": 0, "removed": 0, "skipped_manual": 0}
	start = getdate(from_date or frappe.db.get_value("Hotel Property", plan.property, "business_date"))
	parent_rows = frappe.get_all(
		RATE_DAY,
		filters={"rate_plan": plan.parent_rate_plan, "rate_date": [">=", start]},
		fields=["room_type", "rate_date", "rate"],
	)
	existing = {
		(row.room_type, getdate(row.rate_date)): row
		for row in frappe.get_all(
			RATE_DAY,
			filters={"rate_plan": plan.name, "rate_date": [">=", start]},
			fields=["name", "room_type", "rate_date", "rate", "is_manual_override", "source"],
		)
	}
	codes = dict(
		frappe.get_all(
			"Room Type", filters={"property": plan.property}, fields=["name", "code"], as_list=True
		)
	)
	now, user = now_datetime(), frappe.session.user
	to_insert, counts = [], {"created": 0, "updated": 0, "removed": 0, "skipped_manual": 0}
	seen = set()
	for row in parent_rows:
		key = (row.room_type, getdate(row.rate_date))
		seen.add(key)
		rate = derive_rate(row.rate, plan)
		current = existing.get(key)
		if current is None:
			to_insert.append(
				[
					rate_day_name(plan.name, codes[row.room_type], row.rate_date),
					user,
					user,
					now,
					now,
					0,
					0,
					plan.property,
					plan.name,
					row.room_type,
					row.rate_date,
					rate,
					plan.currency,
					"Derivation",
					0,
					None,
				]
			)
			counts["created"] += 1
		elif current.is_manual_override and not overwrite_manual:
			counts["skipped_manual"] += 1
		elif flt(current.rate) != rate or current.is_manual_override or current.source != "Derivation":
			frappe.db.set_value(
				RATE_DAY,
				current.name,
				{"rate": rate, "source": "Derivation", "season": None, "is_manual_override": 0},
			)
			counts["updated"] += 1
	for key, current in existing.items():
		if key not in seen and current.source == "Derivation" and not current.is_manual_override:
			frappe.db.delete(RATE_DAY, current.name)
			counts["removed"] += 1
	if to_insert:
		frappe.db.bulk_insert(
			RATE_DAY,
			[
				"name",
				"owner",
				"modified_by",
				"creation",
				"modified",
				"docstatus",
				"idx",
				"property",
				"rate_plan",
				"room_type",
				"rate_date",
				"rate",
				"currency",
				"source",
				"is_manual_override",
				"season",
			],
			to_insert,
			ignore_duplicates=True,
		)
	plan.db_set("last_derived_on", now, update_modified=False)
	log_event(
		"Rate Plan",
		plan.name,
		"Rates Derived",
		data={
			**counts,
			"parent": plan.parent_rate_plan,
			"from": str(start),
			"overwrite_manual": bool(overwrite_manual),
		},
		property_name=plan.property,
	)
	# Plans derived from this one follow.
	schedule_derivation([plan.name])
	return counts


# --------------------------------------------------------------------------- bulk edits (F13)


def set_rates(
	rate_plan: str,
	room_types: list[str],
	nights: list,
	*,
	rate=None,
	adjust_percent=None,
	adjust_amount=None,
	reason: str | None = None,
) -> dict:
	"""Set, or adjust by a percentage or an amount, the rate of each room type and night.

	The result is a hand-set rate (a manual override on a derived plan). Nights a room type has no
	rate for are only created by `rate`, not by an adjustment. Plans derived from this one are
	regenerated in the background. Returns {"created", "updated"}.
	"""
	from frappoint.vuna_hospitality.services.restrictions import MAX_BULK_NIGHTS

	nights = sorted({getdate(night) for night in nights})
	if not nights or not room_types:
		frappe.throw(_("Choose the room types and nights to change."))
	if len(nights) > MAX_BULK_NIGHTS:
		frappe.throw(_("Change at most {0} nights at once.").format(MAX_BULK_NIGHTS))
	modes = [value for value in (rate, adjust_percent, adjust_amount) if value not in (None, "")]
	if len(modes) != 1:
		frappe.throw(_("Give a new rate, or a percentage or amount to adjust by."))
	plan = frappe.db.get_value("Rate Plan", rate_plan, ["name", "property", "currency"], as_dict=True)
	existing = {
		(row.room_type, getdate(row.rate_date)): row
		for row in frappe.get_all(
			RATE_DAY,
			filters={
				"rate_plan": rate_plan,
				"room_type": ["in", room_types],
				"rate_date": ["between", [nights[0], nights[-1]]],
			},
			fields=["name", "room_type", "rate_date", "rate"],
		)
	}
	counts = {"created": 0, "updated": 0}
	for room_type in room_types:
		if frappe.db.get_value("Room Type", room_type, "property") != plan.property:
			frappe.throw(_("Room Type {0} belongs to another property.").format(room_type))
		for night in nights:
			current = existing.get((room_type, night))
			if rate not in (None, ""):
				new_rate = flt(rate)
			elif current is None:
				continue
			elif adjust_percent not in (None, ""):
				new_rate = flt(
					Decimal(str(flt(current.rate)))
					* (Decimal(100) + Decimal(str(flt(adjust_percent))))
					/ Decimal(100),
					2,
				)
			else:
				new_rate = flt(flt(current.rate) + flt(adjust_amount), 2)
			if new_rate < 0:
				frappe.throw(
					_("A rate cannot be negative ({0} on {1}).").format(
						room_type, frappe.format(night, "Date")
					)
				)
			if current is None:
				doc = frappe.get_doc(
					{
						"doctype": RATE_DAY,
						"rate_plan": rate_plan,
						"room_type": room_type,
						"rate_date": night,
						"rate": new_rate,
						"currency": plan.currency,
					}
				)
				doc.flags.in_bulk = True
				doc.insert(ignore_permissions=True)
				counts["created"] += 1
			elif flt(current.rate) != new_rate:
				doc = frappe.get_doc(RATE_DAY, current.name)
				doc.rate = new_rate
				doc.flags.in_bulk = True
				doc.save(ignore_permissions=True)
				counts["updated"] += 1
	log_event(
		"Rate Plan",
		rate_plan,
		"Rates Updated",
		reason=(reason or "").strip() or None,
		data={
			**counts,
			"room_types": room_types,
			"from": str(nights[0]),
			"to": str(nights[-1]),
			"nights": len(nights),
			"rate": rate,
			"adjust_percent": adjust_percent,
			"adjust_amount": adjust_amount,
		},
		property_name=plan.property,
	)
	schedule_derivation([rate_plan])
	return counts


def reset_to_derived(rate_plan: str, room_types: list[str], nights: list) -> dict:
	"""Drop the manual overrides on a derived plan for these nights; they take the derived rate."""
	plan = frappe.get_doc("Rate Plan", rate_plan)
	if not plan.parent_rate_plan:
		frappe.throw(_("Rate Plan {0} isn't derived from another plan.").format(rate_plan))
	nights = sorted({getdate(night) for night in nights})
	names = frappe.get_all(
		RATE_DAY,
		filters={
			"rate_plan": rate_plan,
			"room_type": ["in", room_types],
			"rate_date": ["in", nights],
			"is_manual_override": 1,
		},
		pluck="name",
	)
	for name in names:
		frappe.db.set_value(RATE_DAY, name, {"is_manual_override": 0, "source": "Derivation"})
	log_event(
		"Rate Plan",
		rate_plan,
		"Rate Overrides Reset",
		data={"room_types": room_types, "from": str(nights[0]), "to": str(nights[-1]), "reset": len(names)},
		property_name=plan.property,
	)
	result = regenerate_derived(rate_plan, from_date=nights[0])
	return {"reset": len(names), **result}
