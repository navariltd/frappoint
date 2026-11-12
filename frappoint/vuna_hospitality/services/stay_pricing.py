"""Occupancy pricing and packages (design §10.4-10.5; feature F9).

A night's price starts from the Room Rate Day and is split into components, each under its own
charge code, so room revenue stays separable:

- **Room**: the base rate for the room type's base adults, less any package component included
  in the rate.
- **Extra adult** and **child band** charges, from the rate plan's Occupancy Pricing Rule. A child's
  age on the arrival date sets the band for the whole stay.
- **Package components** (breakfast, a spa credit): carved out of the rate, or added to it.
  Allowance components can be redeemed later at an outlet.

The components are snapshotted on each Stay Rate Night when the stay is held. Night audit posts
exactly these lines, and they always sum to the night's total: the room line absorbs any
rounding. Amounts are worked in integer minor units.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

ROOM, EXTRA, CHILD, PACKAGE = "Room", "Extra", "Child", "Package"


class PricingError(frappe.ValidationError):
	"""The night can't be priced: a package worth more than the rate, or a missing charge code."""


@dataclass
class PricingContext:
	"""What pricing a stay needs, loaded once for all its nights."""

	plan: frappe._dict
	base_adults: int
	adults: int
	child_ages: list[int | None]
	arrival: date
	departure: date
	rule: frappe._dict | None = None
	bands: list = field(default_factory=list)
	components: list = field(default_factory=list)

	@property
	def children(self) -> int:
		return len(self.child_ages)


def pricing_context(plan, room_type: str, arrival, departure, adults: int, child_ages) -> PricingContext:
	base_adults = cint(frappe.db.get_value("Room Type", room_type, "base_adults")) or 1
	context = PricingContext(
		plan=plan,
		base_adults=base_adults,
		adults=cint(adults),
		child_ages=list(child_ages),
		arrival=getdate(arrival),
		departure=getdate(departure),
	)
	context.rule = occupancy_rule(plan.name, room_type)
	if context.rule:
		context.bands = frappe.get_all(
			"Occupancy Child Band",
			filters={"parent": context.rule.name, "parenttype": "Occupancy Pricing Rule"},
			fields=["band_name", "from_age", "to_age", "price_as_adult", "amount", "charge_code"],
			order_by="idx asc",
		)
	package = frappe.db.get_value("Rate Plan", plan.name, "package")
	if package and frappe.db.get_value("Hotel Package", package, "is_active"):
		context.components = frappe.get_all(
			"Hotel Package Component",
			filters={"parent": package, "parenttype": "Hotel Package"},
			fields=[
				"name",
				"component_name",
				"charge_code",
				"amount_basis",
				"amount_type",
				"amount",
				"posting_rhythm",
				"included_in_rate",
				"is_allowance",
				"allowance_charge_code",
				"valid_days",
				"breakage_rule",
			],
			order_by="idx asc",
		)
	return context


def occupancy_rule(rate_plan: str, room_type: str) -> frappe._dict | None:
	"""The active rule for the plan and room type, else the plan's rule for every room type."""
	for filters in ({"room_type": room_type}, {"room_type": ["is", "not set"]}):
		rule = frappe.db.get_value(
			"Occupancy Pricing Rule",
			{"rate_plan": rate_plan, "is_active": 1, **filters},
			["name", "extra_adult_amount", "extra_adult_charge_code"],
			as_dict=True,
		)
		if rule:
			return rule
	return None


def child_band(context: PricingContext, age: int | None) -> frappe._dict | None:
	"""The band for a child's age on arrival. Without an age, the oldest band that isn't priced as
	an adult, so an unknown age is never priced below the oldest children's band."""
	if not context.bands:
		return None
	if age is None:
		candidates = [band for band in context.bands if not band.price_as_adult]
		return max(candidates, key=lambda band: band.to_age) if candidates else context.bands[-1]
	return next((band for band in context.bands if band.from_age <= age <= band.to_age), None)


def price_night(
	context: PricingContext, night: date, room_rate_minor: int, to_minor
) -> tuple[list[dict], dict]:
	"""Split one night into components. Returns (components, totals in minor units)."""
	plan = context.plan
	components: list[dict] = []
	extras_minor = 0

	# Children priced as adults count with the adults; the rest fall into their bands.
	adults_for_price = context.adults
	child_lines: dict[str, list] = {}
	for age in context.child_ages:
		band = child_band(context, age)
		if band and band.price_as_adult:
			adults_for_price += 1
		elif band and flt(band.amount):
			child_lines.setdefault(band.band_name, [band, 0])[1] += 1

	rule = context.rule
	extra_adults = max(0, adults_for_price - context.base_adults)
	if rule and extra_adults and flt(rule.extra_adult_amount):
		amount = to_minor(rule.extra_adult_amount) * extra_adults
		extras_minor += amount
		components.append(
			_component(
				"extra-adult",
				EXTRA,
				rule.extra_adult_charge_code,
				_("Extra adult x {0}").format(extra_adults),
				amount,
			)
		)
	for band_name, (band, count) in child_lines.items():
		amount = to_minor(band.amount) * count
		extras_minor += amount
		components.append(
			_component(
				f"child:{band_name}", CHILD, band.charge_code, _("{0} x {1}").format(band_name, count), amount
			)
		)

	carved_minor = added_minor = 0
	for component in context.components:
		if not _posts_on(component, night, context):
			continue
		count = _count(component.amount_basis, context.adults, context.children)
		if not count:
			continue
		if component.amount_type == "Percentage":
			unit = int(
				(Decimal(room_rate_minor) * Decimal(str(component.amount)) / 100).quantize(
					Decimal(1), rounding=ROUND_HALF_UP
				)
			)
		else:
			unit = to_minor(component.amount)
		amount = unit * count
		if component.included_in_rate:
			carved_minor += amount
		else:
			added_minor += amount
		line = _component(
			f"pkg:{component.name}",
			PACKAGE,
			component.charge_code,
			_("{0} x {1}").format(component.component_name, count) if count > 1 else component.component_name,
			amount,
		)
		if component.is_allowance:
			line["allowance"] = {
				"charge_code": component.allowance_charge_code,
				"valid_days": cint(component.valid_days) or 1,
				"breakage_rule": component.breakage_rule or "Breakage Income",
			}
		components.append(line)

	room_minor = room_rate_minor - carved_minor
	if room_minor < 0:
		frappe.throw(
			_("The package on {0} is worth more than the room rate on {1}.").format(
				plan.rate_plan_name, frappe.format(night, "Date")
			),
			PricingError,
		)
	components.insert(0, _component("room", ROOM, plan.room_charge_code, _("Room"), room_minor))
	total_minor = room_rate_minor + extras_minor + added_minor
	return components, {
		"room_rate": room_rate_minor,
		"extras": extras_minor,
		"package": added_minor,
		"total": total_minor,
	}


def _component(key: str, kind: str, charge_code: str | None, label: str, amount_minor: int) -> dict:
	if amount_minor and not charge_code:
		frappe.throw(_("{0} has an amount but no charge code.").format(label), PricingError)
	return {
		"key": key,
		"kind": kind,
		"charge_code": charge_code,
		"label": label,
		"amount_minor": amount_minor,
	}


def _posts_on(component, night: date, context: PricingContext) -> bool:
	if component.amount_basis == "Per Stay" or component.posting_rhythm == "Arrival Night":
		return night == context.arrival
	if component.posting_rhythm == "Last Night":
		return night == frappe.utils.add_days(context.departure, -1)
	return True


def _count(basis: str, adults: int, children: int) -> int:
	return {
		"Per Night": 1,
		"Per Stay": 1,
		"Per Adult": adults,
		"Per Child": children,
		"Per Person": adults + children,
	}.get(basis, 1)


def child_ages_on(arrival, birth_dates) -> list[int]:
	"""Ages on the arrival date, for children whose birth dates are known."""
	arrival = getdate(arrival)
	ages = []
	for born in birth_dates:
		born = getdate(born)
		ages.append(arrival.year - born.year - ((arrival.month, arrival.day) < (born.month, born.day)))
	return ages


def normalize_child_ages(children, child_ages) -> list[int | None]:
	"""`child_ages` (a list, or its JSON) padded with unknown ages up to `children`."""
	if isinstance(child_ages, str):
		child_ages = frappe.parse_json(child_ages) if child_ages.strip() else []
	ages: list[int | None] = []
	for age in child_ages or []:
		if age in (None, ""):
			ages.append(None)
			continue
		age = cint(age)
		if age < 0 or age > 17:
			frappe.throw(_("A child's age must be between 0 and 17."), PricingError)
		ages.append(age)
	children = max(cint(children), len(ages))
	return ages + [None] * (children - len(ages))
