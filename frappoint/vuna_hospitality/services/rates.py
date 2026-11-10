"""Room rates (design §10.1-10.2; feature F3).

Room Rate Day is the only place a price lives: one row per rate plan, room type and night. Seasons
(and, in F13, derived plans and bulk updates) are tools that write Room Rate Days; nothing reads a
season at booking time.
"""

from datetime import date

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
