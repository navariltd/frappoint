"""Money in integer minor units (cents), so sums and splits never drift by rounding."""

from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe.utils import cint

DEFAULT_FRACTION_UNITS = 100


def fraction_units(currency: str | None) -> int:
	"""How many minor units make one major unit (KES, USD: 100; JPY: 1)."""
	if not currency:
		return DEFAULT_FRACTION_UNITS
	units = frappe.get_cached_value("Currency", currency, "fraction_units")
	return cint(units) or DEFAULT_FRACTION_UNITS


def to_minor(amount, currency: str | None) -> int:
	"""12,345.675 KES -> 1234568 (half-up, like a cashier would round)."""
	scaled = Decimal(str(amount or 0)) * fraction_units(currency)
	return int(scaled.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def from_minor(minor: int, currency: str | None) -> float:
	return float(Decimal(int(minor)) / fraction_units(currency))
