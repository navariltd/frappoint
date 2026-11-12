"""Quote a stay (design §10.7; feature F3: steps 1, 3 and 7).

For each night, in order:

1. the room type must be available (ignoring the overbooking allowance);
3. the rate plan must have a Room Rate Day for the room type and night;
7. per-night lines and a stay total are returned.

4. occupancy pricing: extra adults and child bands (F9);
5. package components added to or carved out of the rate (F9);
6. tax on the stay, computed by ERPNext for display (F9).

Step 2 (restrictions) arrives with F13. A quote reads only: it never creates, locks or stores
anything, and the same inputs and master data always give the same quote. Amounts are summed in
integer minor units. Each night carries its components, which a hold snapshots onto the stay.
"""

from dataclasses import asdict, dataclass, field
from datetime import date

import frappe
from frappe import _
from frappe.utils import cint, getdate

from frappoint.vuna_hospitality.services.inventory import nights_between, peek_rows
from frappoint.vuna_hospitality.services.money import from_minor, to_minor
from frappoint.vuna_hospitality.services.rates import get_rates
from frappoint.vuna_hospitality.services.stay_pricing import (
	PricingError,
	normalize_child_ages,
	price_night,
	pricing_context,
)
from frappoint.vuna_hospitality.services.taxes import compute_lines

SOLD_OUT = "Sold Out"
NO_RATE = "No Rate"
TOO_MANY_GUESTS = "Too Many Guests"
PRICING_ERROR = "Pricing Error"


@dataclass
class QuoteNight:
	night: date
	available: int
	rate: float | None
	amount_minor: int
	sellable: bool
	reason: str | None = None
	room_rate_minor: int = 0
	extras_minor: int = 0
	package_minor: int = 0
	components: list[dict] = field(default_factory=list)


@dataclass
class Quote:
	property: str
	rate_plan: str
	rate_plan_name: str
	room_type: str
	room_type_name: str
	arrival: date
	departure: date
	adults: int
	children: int
	currency: str
	tax_inclusive: bool
	child_ages: list[int | None] = field(default_factory=list)
	nights: list[QuoteNight] = field(default_factory=list)
	total_minor: int = 0
	total: float = 0.0
	tax: float = 0.0
	grand_total: float = 0.0
	offered: bool = False
	reasons: list[str] = field(default_factory=list)

	def as_dict(self) -> dict:
		data = asdict(self)
		data["night_count"] = len(self.nights)
		data["average_rate"] = (
			round(self.total / len(self.nights), 2) if self.nights and self.offered else None
		)
		return data


def quote(
	property_name: str,
	arrival,
	departure,
	room_type: str,
	rate_plan: str,
	adults: int = 1,
	children: int = 0,
	child_ages=None,
	with_tax: bool = True,
) -> Quote:
	"""Price one room type on one rate plan for the stay. Check `.offered` and `.reasons`.

	`child_ages` are the children's ages on the arrival date; children without an age are priced in
	the oldest child band.
	"""
	arrival, departure = getdate(arrival), getdate(departure)
	nights = nights_between(arrival, departure)
	ages = normalize_child_ages(children, child_ages)
	adults, children = cint(adults), len(ages)
	if adults < 1:
		frappe.throw(_("A stay needs at least one adult."))

	plan = _get_rate_plan(rate_plan, property_name)
	room = _get_room_type(room_type, property_name)

	result = Quote(
		property=property_name,
		rate_plan=plan.name,
		rate_plan_name=plan.rate_plan_name,
		room_type=room.name,
		room_type_name=room.room_type_name,
		arrival=arrival,
		departure=departure,
		adults=adults,
		children=children,
		currency=plan.currency,
		tax_inclusive=bool(plan.tax_inclusive),
		child_ages=ages,
	)
	context = pricing_context(plan, room.name, arrival, departure, adults, ages)
	minor = lambda amount: to_minor(amount, plan.currency)  # noqa: E731

	if adults > room.max_adults or children > room.max_children or adults + children > room.max_occupancy:
		result.reasons.append(TOO_MANY_GUESTS)

	inventory = peek_rows([room.name], nights)
	rates = get_rates(plan.name, room.name, nights)

	for night in nights:
		row = inventory.get((room.name, night))
		available = cint(row["available"]) - cint(row["overbooking_limit"]) if row else 0
		rate = rates.get(night)
		reason = SOLD_OUT if available < 1 else NO_RATE if rate is None else None
		line = QuoteNight(
			night=night,
			available=max(available, 0),
			rate=rate,
			amount_minor=0,
			sellable=reason is None,
			reason=reason,
		)
		if rate is not None:
			try:
				line.components, totals = price_night(context, night, minor(rate), minor)
			except PricingError as error:
				line.reason, line.sellable = str(error), False
				reason = PRICING_ERROR
			else:
				line.amount_minor = totals["total"]
				line.room_rate_minor = totals["room_rate"]
				line.extras_minor = totals["extras"]
				line.package_minor = totals["package"]
		amount_minor = line.amount_minor
		result.nights.append(line)
		result.total_minor += amount_minor
		if reason and reason not in result.reasons:
			result.reasons.append(reason)

	result.total = from_minor(result.total_minor, plan.currency)
	result.offered = not result.reasons
	result.grand_total = result.total
	if with_tax and result.offered:
		_add_tax(result, property_name)
	return result


def _add_tax(result: Quote, property_name: str) -> None:
	"""Step 6: the tax ERPNext will charge on the stay's lines, for display only."""
	items = {}
	for night in result.nights:
		for component in night.components:
			if component["amount_minor"]:
				item = items.setdefault(
					component["charge_code"],
					frappe.db.get_value("Charge Code", component["charge_code"], "item"),
				)
				component["item"] = item
	lines: dict[str, int] = {}
	for night in result.nights:
		for component in night.components:
			if component["amount_minor"]:
				lines[component["item"]] = lines.get(component["item"], 0) + component["amount_minor"]
	tax = compute_lines(
		property_name,
		[(item, from_minor(amount, result.currency), 1) for item, amount in lines.items()],
		inclusive=result.tax_inclusive,
		on_date=result.arrival,
	)
	result.tax = from_minor(tax.tax_minor, result.currency)
	result.grand_total = from_minor(
		result.total_minor + (0 if result.tax_inclusive else tax.tax_minor), result.currency
	)


def search(
	property_name: str,
	arrival,
	departure,
	adults: int = 1,
	children: int = 0,
	rate_plan: str | None = None,
	room_type: str | None = None,
	child_ages=None,
) -> list[Quote]:
	"""Quote every active room type on every active nightly rate plan (or the ones given).

	Offered quotes come first, cheapest first.
	"""
	plan_filters = {"property": property_name, "is_active": 1, "rate_basis": "Night"}
	if rate_plan:
		plan_filters["name"] = rate_plan
	room_filters = {"property": property_name, "is_active": 1}
	if room_type:
		room_filters["name"] = room_type

	plans = frappe.get_all("Rate Plan", filters=plan_filters, pluck="name", order_by="rate_plan_name")
	room_types = frappe.get_all(
		"Room Type", filters=room_filters, pluck="name", order_by="sort_order, room_type_name"
	)
	quotes = [
		quote(property_name, arrival, departure, rt, plan, adults, children, child_ages)
		for rt in room_types
		for plan in plans
	]
	return sorted(quotes, key=lambda q: (not q.offered, q.total_minor if q.offered else 0, q.room_type_name))


def _get_rate_plan(rate_plan: str, property_name: str):
	plan = frappe.db.get_value(
		"Rate Plan",
		rate_plan,
		[
			"name",
			"property",
			"rate_plan_name",
			"currency",
			"tax_inclusive",
			"is_active",
			"rate_basis",
			"room_charge_code",
		],
		as_dict=True,
	)
	if not plan or plan.property != property_name:
		frappe.throw(_("Rate Plan {0} does not belong to property {1}.").format(rate_plan, property_name))
	if not plan.is_active:
		frappe.throw(_("Rate Plan {0} is inactive.").format(plan.rate_plan_name))
	if plan.rate_basis != "Night":
		frappe.throw(
			_("Rate Plan {0} is a day-use plan; quote day use separately.").format(plan.rate_plan_name)
		)
	return plan


def _get_room_type(room_type: str, property_name: str):
	room = frappe.db.get_value(
		"Room Type",
		room_type,
		["name", "property", "room_type_name", "is_active", "max_adults", "max_children", "max_occupancy"],
		as_dict=True,
	)
	if not room or room.property != property_name:
		frappe.throw(_("Room Type {0} does not belong to property {1}.").format(room_type, property_name))
	if not room.is_active:
		frappe.throw(_("Room Type {0} is inactive.").format(room.room_type_name))
	return room
