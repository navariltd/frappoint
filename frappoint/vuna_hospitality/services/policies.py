"""Cancellation, no-show, and early-departure fees from the stay's policy snapshot (design §11.2,
§16.4; feature F12).

A stay copies its rate plan's policies when it is held, so a policy changed later never changes a
booking already made. Each fee is one folio charge with the key `fee:<stay>:<policy>:<event>`, so
it posts once however often the command runs. A stay reinstated and then cancelled again gets a
new key (`cancellation-2`), because the first fee was reversed.

Fee bases:

- **Cancellation** and **No-show**: the nights given up (all of the stay's unposted nights).
  A cancellation is free until the policy's hours before arrival (arrival date at the property's
  check-in time, in the property's time zone). With 0 hours there is no free period: a
  non-refundable rate charges any cancellation.
- **Early departure**: the nights after the day the guest leaves.

`First Night` charges the first of those nights, `Percentage of Stay` a share of them, `Full Stay`
all of them, and `Fixed Amount` the policy's amount. The fee is tax-inclusive: ERPNext splits out
the tax with the property's template, as for any other charge.
"""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import flt, get_time, getdate

from frappoint.vuna_hospitality.constants import FOLIO_MANAGER_ROLES
from frappoint.vuna_hospitality.services import folio
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.money import from_minor, to_minor
from frappoint.vuna_hospitality.services.reservations import RATE_NIGHT, STAY, _row

CANCELLATION = "Cancellation"
NO_SHOW = "No-show"
EARLY_DEPARTURE = "Early Departure"
SNAPSHOT_FIELDS = {
	CANCELLATION: "cancellation_policy_snapshot",
	NO_SHOW: "no_show_policy_snapshot",
	EARLY_DEPARTURE: "early_departure_policy_snapshot",
}
EVENT_KEYS = {CANCELLATION: "cancellation", NO_SHOW: "no-show", EARLY_DEPARTURE: "early-departure"}
NO_FEE = "None"
DEFAULT_CHECK_IN = "14:00:00"


class PolicyFeeError(frappe.ValidationError):
	pass


def snapshot(stay, event: str) -> frappe._dict | None:
	"""The policy as booked, or None if the stay has none for `event`."""
	value = (
		stay.get(SNAPSHOT_FIELDS[event]) if isinstance(stay, dict) else getattr(stay, SNAPSHOT_FIELDS[event])
	)
	if not value:
		return None
	return frappe._dict(frappe.parse_json(value))


def policy_amount(kind: str, value, nights_minor: list[int], currency: str) -> int:
	"""Minor units a policy asks for over `nights_minor`, the nights it applies to."""
	if not kind or kind == NO_FEE:
		return 0
	if kind == "Fixed Amount":
		return to_minor(value, currency)
	if not nights_minor:
		return 0
	if kind == "First Night":
		return nights_minor[0]
	if kind == "Full Stay":
		return sum(nights_minor)
	if kind == "Percentage of Stay":
		share = Decimal(sum(nights_minor)) * Decimal(str(flt(value))) / 100
		return int(share.quantize(Decimal(1), rounding=ROUND_HALF_UP))
	frappe.throw(_("Unknown policy amount type {0}.").format(kind), PolicyFeeError)


def pending_nights(stay_name: str, from_date=None) -> list[int]:
	"""Minor units of the stay's unposted nights (from `from_date` on), in date order."""
	filters = {"stay_reservation": stay_name, "posting_state": "Pending"}
	if from_date:
		filters["night_date"] = [">=", getdate(from_date)]
	currency = frappe.db.get_value(STAY, stay_name, "currency")
	totals = frappe.get_all(RATE_NIGHT, filters=filters, pluck="total", order_by="night_date asc")
	return [to_minor(total, currency) for total in totals]


def free_cancellation_until(stay) -> datetime | None:
	"""When free cancellation ends, in the property's local time. None when there's no fee at all,
	or no free period (0 hours: every cancellation is charged)."""
	policy = snapshot(stay, CANCELLATION)
	if not policy or (policy.fee_type or NO_FEE) == NO_FEE:
		return None
	if flt(policy.free_until_hours_before_arrival) <= 0:
		return None
	check_in = frappe.db.get_value("Hotel Property", stay.property, "check_in_time") or DEFAULT_CHECK_IN
	arrival = datetime.combine(getdate(stay.arrival_date), get_time(check_in))
	return arrival - timedelta(hours=flt(policy.free_until_hours_before_arrival))


def local_now(property_name: str) -> datetime:
	zone = frappe.db.get_value("Hotel Property", property_name, "time_zone")
	return datetime.now(ZoneInfo(zone)).replace(tzinfo=None) if zone else datetime.now()


def fee_quote(stay, event: str, from_date=None) -> frappe._dict:
	"""What `event` would charge now: {amount, amount_minor, policy, policy_name, free_until}."""
	policy = snapshot(stay, event)
	result = frappe._dict(amount=0, amount_minor=0, policy=None, policy_name=None, free_until=None)
	if not policy or (policy.fee_type or NO_FEE) == NO_FEE:
		return result
	result.update(policy=policy.name, policy_name=policy.policy_name, guest_text=policy.guest_text)
	if event == CANCELLATION:
		result.free_until = free_cancellation_until(stay)
		if result.free_until and local_now(stay.property) < result.free_until:
			return result
	nights = pending_nights(stay.name, from_date)
	result.amount_minor = policy_amount(policy.fee_type, policy.fee_value, nights, stay.currency)
	result.amount = from_minor(result.amount_minor, stay.currency)
	return result


def post_fee(
	stay,
	event: str,
	*,
	from_date=None,
	waive: bool = False,
	waive_reason: str | None = None,
	business_date=None,
) -> dict | None:
	"""Charge the stay's `event` fee, exactly once. Returns {"name", "amount", "folio"} or None.

	Call it before the stay's nights are cancelled: the fee is worked out from them. `waive` (a
	Front Desk Manager, with a reason) skips the fee and records why.
	"""
	quote = fee_quote(stay, event, from_date)
	if not quote.amount_minor:
		return None
	if waive:
		if not set(FOLIO_MANAGER_ROLES) & set(frappe.get_roles()):
			frappe.throw(
				_("Only a Front Desk Manager can waive a {0} fee.").format(_(event).lower()),
				frappe.PermissionError,
			)
		waive_reason = (waive_reason or "").strip()
		if not waive_reason:
			frappe.throw(_("Give a reason for waiving the fee."), PolicyFeeError)
		log_event(
			STAY,
			stay.name,
			"Policy Fee Waived",
			reason=waive_reason,
			data={"event": event, "policy": quote.policy, "amount": quote.amount},
		)
		return None

	code = frappe.db.get_value("Hotel Property", stay.property, "policy_fee_charge_code")
	if not code:
		frappe.throw(
			_(
				"The {0} policy charges {1}, but Hotel Property {2} has no Policy Fee Charge Code to post it with."
			).format(quote.policy_name, quote.amount, stay.property),
			PolicyFeeError,
		)
	from frappoint.vuna_hospitality.services.routing import destination

	target = destination(stay.name, code)
	key = f"fee:{stay.name}:{quote.policy}:{EVENT_KEYS[event]}{_round_suffix(stay.name)}"
	result = folio.post(
		target,
		code,
		quote.amount,
		posting_key=key,
		tax_inclusive=True,
		description=_("{0} fee: {1}").format(_(event), quote.policy_name)[:140],
		business_date=business_date,
		service_date=business_date or folio._business_date(stay.property),
		source_doctype=STAY,
		source_name=stay.name,
		source_line=EVENT_KEYS[event],
	)
	if result["created"]:
		log_event(
			STAY,
			stay.name,
			"Policy Fee Posted",
			data={
				"event": event,
				"policy": quote.policy,
				"amount": quote.amount,
				"transaction": result["name"],
			},
		)
	return {"name": result["name"], "amount": quote.amount, "folio": target}


def _round_suffix(stay_name: str) -> str:
	"""Nothing the first time; "-2", "-3" after each reinstatement, whose reversal undid the fee."""
	rounds = frappe.db.count(
		"Hospitality Event Log",
		{"reference_doctype": STAY, "reference_name": stay_name, "event_type": "Reservation Reinstated"},
	)
	return f"-{rounds + 1}" if rounds else ""


def fee_lines(stay_name: str) -> list:
	"""The stay's policy fee lines that aren't reversed."""
	lines = frappe.get_all(
		folio.TRANSACTION,
		filters={
			"stay_reservation": stay_name,
			"posting_key": ["like", f"fee:{stay_name}:%"],
			"docstatus": 1,
		},
		fields=["name", "guest_folio", "gross_amount", "sales_invoice", "posting_key"],
	)
	reversed_lines = set(
		frappe.get_all(
			folio.TRANSACTION,
			filters={"reverses": ["in", [line.name for line in lines] or [""]], "docstatus": 1},
			pluck="reverses",
		)
	)
	return [line for line in lines if line.name not in reversed_lines]


def stay_policies(stay) -> list[dict]:
	"""The stay's booked policies, as the desk shows them."""
	rows = []
	for event in (CANCELLATION, NO_SHOW, EARLY_DEPARTURE):
		policy = snapshot(stay, event)
		if policy:
			rows.append(
				{
					"event": event,
					"policy_name": policy.policy_name,
					"fee_type": policy.fee_type,
					"fee_value": policy.fee_value,
					"free_until_hours_before_arrival": policy.free_until_hours_before_arrival,
					"guest_text": policy.guest_text,
				}
			)
	return rows
