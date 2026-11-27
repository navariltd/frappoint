"""Independent room sharers (design §12.3 to §12.5, §6.2; plan R2-1).

Two or more **Stay Reservations** share one **Room Occupancy**: each keeps its own dates, rate plan,
folio, invoice and check-in and check-out, while the room is counted **once** in inventory. Each
stay's link to the occupancy is a dated **Occupancy Membership**, so the occupancy spans from the
first sharer's arrival to the last one's departure.

Switched on by **Allow Independent Room Share** in Hospitality Settings. When it is off, new shares
are refused; shares already made carry on, so their stays still check in and out, cancel and post.

**Joining.** The joining stay (confirmed, not arrived) gives its own rooms back and gets a
membership on the other stay's occupancy (reason *Join*). The occupancy grows to cover both stays,
taking under the inventory lock only the nights it didn't hold already. They must be the same room
type, be in the room together for at least one night, and fit the room's capacity on every night.
Combining stays from different bookings is a manager's action; the bookings are not merged.

**Splitting the room charge** (`redistribute`). On each night two or more sharers are present, the
room charge (the primary stay's room rate) is split by the occupancy's method:

- *Own Rate*: each stay pays its own rate;
- *Equal Split*: equal parts, any cent left over to the primary stay;
- *Percentage*: the primary stay pays its percentage, the others share the rest;
- *Entire to One*: one stay pays the room, the others nothing for it.

Only the room part is split; each stay keeps its own extras, packages and per-person levies, and a
per-room levy is charged once, to the primary stay (or the payer). The parts always add up to the
room charge, and the night records the split (`share_distribution`). Posted nights never change.
On a night only one sharer is present (a staggered stay) that stay pays its own rate.

**Leaving.** A stay that is cancelled, a no-show, leaves early or checks out ends its membership.
The occupancy shrinks to the stays still in it and gives back only the nights nobody needs (never a
night already used), the room stays occupied for the others, and the charge is split again. A
sharer who hasn't arrived can also **separate** into a room of their own (reason *Separate*).
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from frappoint.vuna_hospitality.constants import RESERVATION_MANAGER_ROLES, RESERVATION_ROLES
from frappoint.vuna_hospitality.services import inventory
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.money import from_minor, to_minor

STAY = "Stay Reservation"
OCCUPANCY = "Room Occupancy"
MEMBERSHIP = "Occupancy Membership"
RATE_NIGHT = "Stay Rate Night"
ASSIGNMENT = "Room Assignment"

SHARED, SINGLE = "Shared", "Single Account"
OWN_RATE, EQUAL, PERCENTAGE, ENTIRE = "Own Rate", "Equal Split", "Percentage", "Entire to One"
METHODS = (OWN_RATE, EQUAL, PERCENTAGE, ENTIRE)
ACTIVE_STAY_STATUSES = ("Held", "Confirmed", "Due In", "In House", "Due Out")
# A stay that checked out still used its nights: the occupancy keeps them.
SPAN_STAY_STATUSES = (*ACTIVE_STAY_STATUSES, "Checked Out")
JOINING_STATUSES = ("Confirmed", "Due In")
HOST_STATUSES = ("Confirmed", "Due In", "In House", "Due Out")
ROOM_KEY = "room"


class ShareError(frappe.ValidationError):
	pass


def enabled() -> bool:
	return bool(cint(frappe.db.get_single_value("Hospitality Settings", "allow_independent_room_share")))


def is_shared(occupancy: str | None) -> bool:
	return bool(occupancy) and frappe.db.get_value(OCCUPANCY, occupancy, "share_mode") == SHARED


# --------------------------------------------------------------------------- members


def members(occupancy: str, exclude: str | None = None, departed: bool = False) -> list[frappe._dict]:
	"""The occupancy's sharers still in it (with `departed`, also those who checked out), each with
	its membership dates and its stay's details. A membership with no nights left is skipped."""
	rows = frappe.get_all(
		MEMBERSHIP,
		filters={"room_occupancy": occupancy},
		fields=["name", "stay_reservation", "start_date", "end_date", "reason"],
		order_by="creation asc",
	)
	if not rows:
		return []
	statuses = SPAN_STAY_STATUSES if departed else ACTIVE_STAY_STATUSES
	stays = {
		stay.name: stay
		for stay in frappe.get_all(
			STAY,
			filters={"name": ["in", [row.stay_reservation for row in rows]]},
			fields=[
				"name",
				"status",
				"lead_guest_name",
				"adults",
				"children",
				"arrival_date",
				"departure_date",
				"hotel_booking",
				"currency",
			],
		)
	}
	found = []
	for row in rows:
		stay = stays.get(row.stay_reservation)
		if not stay or stay.name == exclude or stay.status not in statuses:
			continue
		if getdate(row.end_date) <= getdate(row.start_date):
			continue
		row.stay = stay
		found.append(row)
	return found


def present(rows: list, night) -> list:
	"""The sharers in the room on `night`."""
	night = getdate(night)
	return [row for row in rows if getdate(row.start_date) <= night < getdate(row.end_date)]


def others_in_room(stay) -> bool:
	"""Whether other sharers still use the stay's room."""
	return is_shared(stay.room_occupancy) and bool(members(stay.room_occupancy, exclude=stay.name))


def others_in_house(stay) -> bool:
	"""Whether another sharer is checked in to the stay's room: then it stays occupied for them."""
	return is_shared(stay.room_occupancy) and any(
		row.stay.status in ("In House", "Due Out") for row in members(stay.room_occupancy, exclude=stay.name)
	)


def guests_of_others(stay) -> tuple[int, int]:
	"""The most adults and children the other sharers have in the room on any night of this stay."""
	if not is_shared(stay.room_occupancy):
		return 0, 0
	rows = members(stay.room_occupancy, exclude=stay.name)
	adults = children = 0
	for night in inventory.nights_between(stay.arrival_date, stay.departure_date):
		here = present(rows, night)
		adults = max(adults, sum(cint(row.stay.adults) for row in here))
		children = max(children, sum(cint(row.stay.children) for row in here))
	return adults, children


def _check_capacity(room_type: str, rows: list) -> None:
	limits = frappe.db.get_value(
		"Room Type",
		room_type,
		["room_type_name", "max_adults", "max_children", "max_occupancy"],
		as_dict=True,
	)
	for night in _span_nights(rows):
		here = present(rows, night)
		adults = sum(cint(row.stay.adults) for row in here)
		children = sum(cint(row.stay.children) for row in here)
		if (
			adults > cint(limits.max_adults)
			or children > cint(limits.max_children)
			or adults + children > cint(limits.max_occupancy)
		):
			frappe.throw(
				_(
					"On {0} the shared room would hold {1} adult(s) and {2} child(ren). A {3} sleeps at most {4} adults, {5} children and {6} people."
				).format(
					frappe.format(night, "Date"),
					adults,
					children,
					limits.room_type_name,
					limits.max_adults,
					limits.max_children,
					limits.max_occupancy,
				),
				ShareError,
			)


def _span_nights(rows: list) -> list:
	if not rows:
		return []
	return inventory.nights_between(
		min(getdate(row.start_date) for row in rows), max(getdate(row.end_date) for row in rows)
	)


# --------------------------------------------------------------------------- the occupancy's span


def edge_ranges(old_start, old_end, new_start, new_end) -> tuple[list, list]:
	"""The nights to give back and to take when an occupancy goes from [old) to [new)."""
	release = [(old_start, min(new_start, old_end)), (max(new_end, old_start), old_end)]
	take = [(new_start, min(old_start, new_end)), (max(old_end, new_start), new_end)]
	return [r for r in release if r[0] < r[1]], [t for t in take if t[0] < t[1]]


def resize(occupancy: str) -> None:
	"""Make the occupancy span its sharers (those who checked out keep their nights), taking or
	giving back nights under the inventory lock. With nobody left it gives everything back.

	The room's assignment follows the new span; it is refused if another stay holds the room on a
	night the sharers now need.
	"""
	from frappoint.vuna_hospitality.services.status_commands import transition

	doc = frappe.get_doc(OCCUPANCY, occupancy)
	if doc.allocation_state not in ("Held", "Confirmed"):
		return
	kind = inventory.HELD if doc.allocation_state == "Held" else inventory.SOLD
	rows = members(occupancy, departed=True)
	old_start, old_end = getdate(doc.start_date), getdate(doc.end_date)
	if not rows:
		inventory.release(doc.room_type, old_start, old_end, kind=kind)
		transition(
			doc,
			"Released",
			updates={"hold_expires_at": None},
			event_type="Allocation Changed",
			ignore_permissions=True,
		)
		return
	nights = _span_nights(rows)
	new_start, new_end = nights[0], max(getdate(row.end_date) for row in rows)
	release, take = edge_ranges(old_start, old_end, new_start, new_end)
	for start, end in take:
		inventory.acquire(doc.room_type, start, end, kind=kind)
	for start, end in release:
		inventory.release(doc.room_type, start, end, kind=kind)
	frappe.db.set_value(
		OCCUPANCY,
		occupancy,
		{
			"start_date": new_start,
			"end_date": new_end,
			"adults": max(sum(cint(row.stay.adults) for row in present(rows, night)) for night in nights),
			"children": max(sum(cint(row.stay.children) for row in present(rows, night)) for night in nights),
		},
	)
	doc.reload()
	_fit_assignment(doc, rows, new_start, new_end)


def _fit_assignment(doc, rows: list, new_start, new_end) -> None:
	from frappoint.vuna_hospitality.services import front_desk

	assignment = front_desk.current_assignment(doc.name)
	if not assignment:
		return
	window_stay = frappe._dict(property=doc.property, arrival_date=new_start, departure_date=new_end)
	start, end = front_desk.stay_window(window_stay)
	if assignment.status == "Occupied":
		# The room has been in use since check-in; only its end moves.
		start = assignment.start_datetime
	turnover = frappe.db.get_value("Hotel Property", doc.property, "turnover_minutes")
	conflict = front_desk.find_conflict(assignment.hotel_room, start, end, turnover, doc.name)
	if conflict:
		frappe.throw(
			_(
				"Room {0} is taken by stay {1} on a night the sharers now need. Move them to another room first."
			).format(assignment.room_number, frappe.db.get_value(ASSIGNMENT, conflict, "stay_reservation")),
			ShareError,
		)
	values = {"end_date": new_end, "end_datetime": end}
	if assignment.status == "Assigned":
		values.update(start_date=new_start, start_datetime=start)
	remaining = {row.stay_reservation for row in rows if row.stay.status in ACTIVE_STAY_STATUSES}
	if remaining and assignment.stay_reservation not in remaining:
		# The assignment names a stay still in the room.
		values["stay_reservation"] = (
			doc.share_primary if doc.share_primary in remaining else sorted(remaining)[0]
		)
	frappe.db.set_value(ASSIGNMENT, assignment.name, values)


# --------------------------------------------------------------------------- splitting the room charge


def split(total_minor: int, stays: list[str], method: str, primary: str, percent, payer) -> dict:
	"""{stay: minor units} adding up to `total_minor` exactly. `stays` is in a stable order."""
	lead = primary if primary in stays else stays[0]
	if method == ENTIRE:
		owner = payer if payer in stays else lead
		return {stay: (total_minor if stay == owner else 0) for stay in stays}
	if method == PERCENTAGE:
		lead_share = round(total_minor * flt(percent) / 100)
		others = [stay for stay in stays if stay != lead]
		if not others:
			return {lead: total_minor}
		rest = total_minor - lead_share
		shares = {stay: rest // len(others) for stay in others}
		shares[others[0]] += rest - sum(shares.values())
		return {lead: lead_share, **shares}
	base = total_minor // len(stays)
	shares = {stay: base for stay in stays}
	shares[lead] += total_minor - base * len(stays)
	return shares


def redistribute(occupancy: str) -> None:
	"""Split the room charge of every pending night two or more sharers spend together, by the
	occupancy's method, and give each stay its own rate back on nights it has the room alone.
	Posted nights are never touched."""
	doc = frappe.get_doc(OCCUPANCY, occupancy)
	rows = members(occupancy)
	if not rows:
		return
	nights = frappe.get_all(
		RATE_NIGHT,
		filters={
			"stay_reservation": ["in", [row.stay_reservation for row in rows]],
			"posting_state": "Pending",
		},
		fields=["name", "stay_reservation", "night_date", "components", "share_distribution", "currency"],
		order_by="stay_reservation asc",
	)
	by_date: dict = {}
	for night in nights:
		if night.stay_reservation in {row.stay_reservation for row in present(rows, night.night_date)}:
			by_date.setdefault(getdate(night.night_date), []).append(night)
	method = doc.share_method or EQUAL
	touched = set()
	for night_date, group in by_date.items():
		originals = {night.name: _original(night) for night in group}
		if len(group) < 2:
			for night in group:
				if night.share_distribution:
					_save_night(night, originals[night.name], None)
					touched.add(night.stay_reservation)
			continue
		stays = [night.stay_reservation for night in group]
		lead = doc.share_primary if doc.share_primary in stays else stays[0]
		currency = next(night.currency for night in group if night.stay_reservation == lead)
		own = {night.stay_reservation: _room_minor(originals[night.name], currency) for night in group}
		if method == OWN_RATE:
			shares = own
		else:
			shares = split(own[lead], stays, method, lead, doc.share_percent, doc.share_payer)
		distribution = {
			"method": method,
			"night": str(night_date),
			"room_charge": from_minor(sum(shares.values()), currency),
			"shares": {stay: from_minor(amount, currency) for stay, amount in shares.items()},
			"levy_payer": doc.share_payer if method == ENTIRE and doc.share_payer in stays else lead,
		}
		for night in group:
			components = [dict(component) for component in originals[night.name]]
			for component in components:
				if component.get("key") == ROOM_KEY:
					component["amount"] = from_minor(shares[night.stay_reservation], currency)
					component["amount_minor"] = shares[night.stay_reservation]
			_save_night(night, components, {**distribution, "original": originals[night.name]})
			touched.add(night.stay_reservation)
	for stay in touched:
		_refresh_stay_total(stay)


def _original(night) -> list:
	"""The night's components as priced, before any split."""
	stored = frappe.parse_json(night.share_distribution) if night.share_distribution else None
	if stored and stored.get("original"):
		return stored["original"]
	return frappe.parse_json(night.components) if night.components else []


def _room_minor(components: list, currency: str) -> int:
	return sum(
		to_minor(component["amount"], currency)
		for component in components
		if component.get("key") == ROOM_KEY
	)


def _save_night(night, components: list, distribution: dict | None) -> None:
	currency = night.currency
	frappe.db.set_value(
		RATE_NIGHT,
		night.name,
		{
			"components": frappe.as_json(components),
			"total": from_minor(sum(to_minor(c["amount"], currency) for c in components), currency),
			"room_rate": from_minor(_room_minor(components, currency), currency),
			"share_distribution": frappe.as_json(distribution) if distribution else None,
		},
		update_modified=False,
	)


def _refresh_stay_total(stay_name: str) -> None:
	from frappoint.vuna_hospitality.services.folio import refresh_stay_pending

	currency = frappe.db.get_value(STAY, stay_name, "currency")
	totals = frappe.get_all(
		RATE_NIGHT,
		filters={"stay_reservation": stay_name, "posting_state": ["!=", "Cancelled"]},
		pluck="total",
	)
	total_minor = sum(to_minor(amount, currency) for amount in totals)
	frappe.db.set_value(
		STAY,
		stay_name,
		{
			"total_amount": from_minor(total_minor, currency),
			"average_rate": from_minor(total_minor // max(len(totals), 1), currency),
		},
		update_modified=False,
	)
	refresh_stay_pending(stay_name)


def _restore_own_rate(stay_name: str) -> None:
	nights = frappe.get_all(
		RATE_NIGHT,
		filters={
			"stay_reservation": stay_name,
			"posting_state": "Pending",
			"share_distribution": ["is", "set"],
		},
		fields=["name", "components", "share_distribution", "currency"],
	)
	for night in nights:
		_save_night(night, _original(night), None)
	if nights:
		_refresh_stay_total(stay_name)


def skip_room_levy(night, stay_name: str) -> bool:
	"""Night audit: a per-room levy is charged once a shared night, to its levy payer."""
	if not night.get("share_distribution"):
		return False
	distribution = frappe.parse_json(night.share_distribution) or {}
	return bool(distribution.get("levy_payer")) and distribution["levy_payer"] != stay_name


def room_tax(night, stay_name: str, property_name: str, charge_code: str, inclusive: bool, on_date):
	"""Night audit: this sharer's part of the tax on the shared room charge, or None to tax the part
	on its own. The tax is computed once on the whole room charge and allocated by share (the
	remainder to the primary stay), so the parts' tax adds up to the room's tax exactly.

	Returns {"amount": gross to post, "tax_amount", "tax_breakdown"}."""
	from frappoint.vuna_hospitality.services import taxes

	distribution = frappe.parse_json(night.get("share_distribution") or "null") or {}
	shares = distribution.get("shares") or {}
	if distribution.get("method") in (None, OWN_RATE) or stay_name not in shares:
		return None
	item = frappe.db.get_value("Charge Code", charge_code, "item")
	currency = night.get("currency") or frappe.db.get_value(STAY, stay_name, "currency")
	whole = taxes.compute(
		property_name, item, distribution["room_charge"], inclusive=inclusive, on_date=on_date
	)
	if not whole.tax_minor:
		return None
	share_minor = {stay: to_minor(amount, currency) for stay, amount in shares.items()}
	total_minor = sum(share_minor.values())
	if not total_minor:
		return None
	lead = (
		distribution.get("levy_payer")
		if distribution.get("levy_payer") in share_minor
		else sorted(share_minor)[0]
	)
	breakdown = []
	for row in whole.breakdown or [
		{"account": None, "description": None, "amount": from_minor(whole.tax_minor, currency)}
	]:
		row_minor = to_minor(row["amount"], currency)
		parts = {stay: row_minor * minor // total_minor for stay, minor in share_minor.items()}
		parts[lead] += row_minor - sum(parts.values())
		breakdown.append({**row, "amount": from_minor(parts[stay_name], currency)})
	tax_minor = sum(to_minor(row["amount"], currency) for row in breakdown)
	gross_minor = share_minor[stay_name] if inclusive else share_minor[stay_name] + tax_minor
	return {
		"amount": from_minor(gross_minor, currency),
		"tax_amount": from_minor(tax_minor, currency),
		"tax_breakdown": [row for row in breakdown if row.get("account")] or None,
	}


# --------------------------------------------------------------------------- reading


def summary(stay_name: str) -> dict:
	"""What the stay page shows: whether sharing is on, who shares the room, and how it is charged."""
	stay = frappe.db.get_value(STAY, stay_name, ["name", "status", "room_occupancy"], as_dict=True)
	occupancy = frappe.db.get_value(
		OCCUPANCY,
		stay.room_occupancy,
		["name", "share_mode", "share_primary", "share_method", "share_percent", "share_payer"],
		as_dict=True,
	)
	shared = bool(occupancy) and occupancy.share_mode == SHARED
	rows = members(occupancy.name, departed=True) if shared else []
	can_book = bool(set(frappe.get_roles()) & set(RESERVATION_ROLES))
	return {
		"enabled": enabled(),
		"shared": shared,
		"occupancy": occupancy.name if occupancy else None,
		"method": occupancy.share_method if shared else None,
		"percent": occupancy.share_percent if shared else None,
		"payer": occupancy.share_payer if shared else None,
		"primary": occupancy.share_primary if shared else None,
		"methods": list(METHODS),
		"members": [
			{
				"stay": row.stay_reservation,
				"guest": row.stay.lead_guest_name,
				"status": row.stay.status,
				"start_date": row.start_date,
				"end_date": row.end_date,
				"booking": row.stay.hotel_booking,
				"adults": row.stay.adults,
				"children": row.stay.children,
				"room_charge": _room_charge(row.stay_reservation),
				"currency": row.stay.currency,
			}
			for row in rows
		],
		"can_join": enabled() and can_book and stay.status in JOINING_STATUSES and not shared,
		"can_separate": can_book and shared and stay.status in JOINING_STATUSES,
		"can_change_method": can_book and shared,
		"can_combine_bookings": bool(set(frappe.get_roles()) & set(RESERVATION_MANAGER_ROLES)),
	}


def _room_charge(stay_name: str) -> float:
	"""The room part of the stay's nights: what it pays for the room, after the split."""
	return sum(
		flt(amount)
		for amount in frappe.get_all(
			RATE_NIGHT,
			filters={"stay_reservation": stay_name, "posting_state": ["in", ("Pending", "Posted")]},
			pluck="room_rate",
		)
	)


def candidates(stay_name: str) -> list[dict]:
	"""Stays this one could join: same property and room type, at least one night together."""
	stay = frappe.db.get_value(
		STAY,
		stay_name,
		["name", "property", "room_type", "arrival_date", "departure_date", "hotel_booking"],
		as_dict=True,
	)
	rows = frappe.get_all(
		STAY,
		filters={
			"property": stay.property,
			"room_type": stay.room_type,
			"status": ["in", HOST_STATUSES],
			"arrival_date": ["<", stay.departure_date],
			"departure_date": [">", stay.arrival_date],
			"name": ["!=", stay.name],
		},
		fields=[
			"name",
			"lead_guest_name",
			"arrival_date",
			"departure_date",
			"status",
			"hotel_booking",
			"adults",
			"children",
			"room_occupancy",
		],
		order_by="arrival_date asc",
		limit_page_length=100,
	)
	for row in rows:
		row.same_booking = row.hotel_booking == stay.hotel_booking
		row.shared = is_shared(row.room_occupancy)
	return rows


# --------------------------------------------------------------------------- commands


def _require(roles, message: str) -> None:
	if not set(roles) & set(frappe.get_roles()):
		raise frappe.PermissionError(message)


def _check_method(method: str, percent, payer, stays) -> None:
	if method not in METHODS:
		frappe.throw(_("Pick how the room charge is split."), ShareError)
	if method == ENTIRE and payer not in stays:
		frappe.throw(_("Pick which stay pays the room."), ShareError)
	if method == PERCENTAGE and not (0 <= flt(percent) <= 100):
		frappe.throw(_("The primary stay's share is between 0 and 100 percent."), ShareError)


def _method_values(method: str, percent, payer) -> dict:
	return {
		"share_method": method,
		"share_percent": flt(percent) if method == PERCENTAGE else 0,
		"share_payer": payer if method == ENTIRE else None,
	}


def join(stay_name: str, with_stay: str, method: str = EQUAL, percent=None, payer=None) -> str:
	"""Put `stay_name` (confirmed, not arrived) in the room of `with_stay`. Returns the occupancy."""
	from frappoint.vuna_hospitality.services import reservations

	if not enabled():
		frappe.throw(_("Room sharing is switched off in Hospitality Settings."), ShareError)
	_require(RESERVATION_ROLES, _("You are not allowed to share rooms."))
	if stay_name == with_stay:
		frappe.throw(_("Pick another stay to share with."), ShareError)
	for name in sorted((stay_name, with_stay)):
		reservations._lock_stay(name)
	sharer = frappe.get_doc(STAY, stay_name)
	host = frappe.get_doc(STAY, with_stay)
	_check_method(method, percent, payer, (sharer.name, host.name))
	if sharer.property != host.property or sharer.room_type != host.room_type:
		frappe.throw(_("Sharers stay at the same property, in the same room type."), ShareError)
	if sharer.status not in JOINING_STATUSES:
		frappe.throw(
			_("Only a confirmed stay that hasn't arrived joins a room. Stay {0} is {1}.").format(
				sharer.name, _(sharer.status)
			),
			ShareError,
		)
	if host.status not in HOST_STATUSES:
		frappe.throw(_("Stay {0} is {1}.").format(host.name, _(host.status)), ShareError)
	if not (
		getdate(sharer.arrival_date) < getdate(host.departure_date)
		and getdate(host.arrival_date) < getdate(sharer.departure_date)
	):
		frappe.throw(_("Sharers must be in the room together for at least one night."), ShareError)
	if sharer.room_occupancy == host.room_occupancy:
		frappe.throw(_("They already share a room."), ShareError)
	if is_shared(sharer.room_occupancy):
		frappe.throw(_("Stay {0} already shares a room. Separate it first.").format(sharer.name), ShareError)
	if sharer.hotel_booking != host.hotel_booking:
		_require(
			RESERVATION_MANAGER_ROLES,
			_("Only a Front Desk or Hospitality Manager can combine stays from different bookings."),
		)

	occupancy = host.room_occupancy
	old_occupancy = sharer.room_occupancy
	old_membership = frappe.db.get_value(
		MEMBERSHIP, {"room_occupancy": old_occupancy, "stay_reservation": sharer.name}, "name"
	)
	# The joining stay's own rooms go back first; the shared occupancy then takes what it lacks.
	reservations._cancel_room_assignment(sharer)
	reservations._release_occupancy(old_occupancy, "Released")
	membership = frappe.get_doc(
		{
			"doctype": MEMBERSHIP,
			"property": host.property,
			"room_occupancy": occupancy,
			"stay_reservation": sharer.name,
			"start_date": sharer.arrival_date,
			"end_date": sharer.departure_date,
			"reason": "Join",
			"previous_membership": old_membership,
		}
	)
	membership.flags[reservations.SERVICE_FLAG] = True
	membership.insert(ignore_permissions=True)
	frappe.db.set_value(STAY, sharer.name, "room_occupancy", occupancy)
	_check_capacity(host.room_type, members(occupancy))
	frappe.db.set_value(
		OCCUPANCY,
		occupancy,
		{
			"share_mode": SHARED,
			"share_primary": frappe.db.get_value(OCCUPANCY, occupancy, "share_primary") or host.name,
			**_method_values(method, percent, payer),
		},
	)
	resize(occupancy)
	redistribute(occupancy)
	for stay, other in ((sharer.name, host.name), (host.name, sharer.name)):
		log_event(
			STAY,
			stay,
			"Room Shared",
			data={"with": other, "occupancy": occupancy, "method": method, "from": old_occupancy},
		)
	reservations.refresh_booking(sharer.hotel_booking)
	if host.hotel_booking != sharer.hotel_booking:
		reservations.refresh_booking(host.hotel_booking)
	return occupancy


def set_method(occupancy: str, method: str, percent=None, payer=None) -> None:
	"""Change how the shared room charge is split. Only nights not yet charged change."""
	_require(RESERVATION_ROLES, _("You are not allowed to change how a shared room is charged."))
	if not is_shared(occupancy):
		frappe.throw(_("The room isn't shared."), ShareError)
	stays = sorted({row.stay_reservation for row in members(occupancy)})
	_check_method(method, percent, payer, stays)
	frappe.db.set_value(OCCUPANCY, occupancy, _method_values(method, percent, payer))
	redistribute(occupancy)
	for stay in stays:
		log_event(
			STAY,
			stay,
			"Room Share Changed",
			data={"occupancy": occupancy, "method": method, "percent": percent, "payer": payer},
		)


def separate(stay_name: str, reason: str) -> str:
	"""A sharer who hasn't arrived takes a room of their own again. Returns their new occupancy."""
	from frappoint.vuna_hospitality.services import reservations
	from frappoint.vuna_hospitality.services.status_commands import transition

	_require(RESERVATION_ROLES, _("You are not allowed to separate a shared room."))
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give the reason for separating the stay."), ShareError)
	stay = reservations._lock_stay(stay_name)
	if stay.status not in JOINING_STATUSES:
		frappe.throw(
			_(
				"Only a sharer who hasn't arrived separates here. An in-house sharer moves room from the front desk."
			),
			ShareError,
		)
	old = stay.room_occupancy
	if not others_in_room(stay):
		frappe.throw(_("Stay {0} doesn't share its room.").format(stay.name), ShareError)
	inventory.acquire(stay.room_type, stay.arrival_date, stay.departure_date, kind=inventory.SOLD)
	new = frappe.get_doc(
		{
			"doctype": OCCUPANCY,
			"property": stay.property,
			"hotel_booking": stay.hotel_booking,
			"room_type": stay.room_type,
			"start_date": stay.arrival_date,
			"end_date": stay.departure_date,
			"allocation_state": "Held",
			"share_mode": SINGLE,
			"adults": stay.adults,
			"children": stay.children,
		}
	)
	new.flags[reservations.SERVICE_FLAG] = True
	new.insert(ignore_permissions=True)
	transition(new, "Confirmed", event_type="Allocation Changed", ignore_permissions=True)
	old_membership = frappe.db.get_value(
		MEMBERSHIP, {"room_occupancy": old, "stay_reservation": stay.name}, "name"
	)
	frappe.db.set_value(MEMBERSHIP, old_membership, "end_date", stay.arrival_date)
	membership = frappe.get_doc(
		{
			"doctype": MEMBERSHIP,
			"property": stay.property,
			"room_occupancy": new.name,
			"stay_reservation": stay.name,
			"start_date": stay.arrival_date,
			"end_date": stay.departure_date,
			"reason": "Separate",
			"previous_membership": old_membership,
		}
	)
	membership.flags[reservations.SERVICE_FLAG] = True
	membership.insert(ignore_permissions=True)
	frappe.db.set_value(STAY, stay.name, "room_occupancy", new.name)
	_after_leaving(old, stay.name)
	_restore_own_rate(stay.name)
	log_event(STAY, stay.name, "Room Share Separated", reason=reason, data={"from": old, "to": new.name})
	reservations.refresh_booking(stay.hotel_booking)
	return new.name


def _after_leaving(occupancy: str, leaving_stay: str) -> None:
	"""Shrink the occupancy to the stays left in it and split the charge again; with one stay left
	the room is a single account again."""
	remaining = sorted({row.stay_reservation for row in members(occupancy)})
	if leaving_stay == frappe.db.get_value(OCCUPANCY, occupancy, "share_primary") and remaining:
		frappe.db.set_value(OCCUPANCY, occupancy, "share_primary", remaining[0])
	resize(occupancy)
	if len(remaining) <= 1:
		frappe.db.set_value(OCCUPANCY, occupancy, "share_mode", SINGLE)
		for stay in remaining:
			_restore_own_rate(stay)
	else:
		redistribute(occupancy)


# --------------------------------------------------------------------------- lifecycle hooks


def release_member(stay, to_state: str) -> bool:
	"""Cancel, no-show and hold expiry: if the stay shares its room with others, take it out of the
	share and return True (the room stays with them). False: the caller releases the room as usual."""
	if not others_in_room(stay):
		return False
	frappe.db.set_value(
		MEMBERSHIP,
		{"room_occupancy": stay.room_occupancy, "stay_reservation": stay.name},
		"end_date",
		stay.arrival_date,
	)
	_after_leaving(stay.room_occupancy, stay.name)
	log_event(STAY, stay.name, "Left Shared Room", data={"occupancy": stay.room_occupancy, "as": to_state})
	return True


def departure_moved(stay, new_departure) -> None:
	"""A sharer leaves earlier or later: move their membership's end, fit the occupancy to everyone
	(taking or giving back only the edge nights), and split the charge again."""
	frappe.db.set_value(
		MEMBERSHIP,
		{"room_occupancy": stay.room_occupancy, "stay_reservation": stay.name},
		"end_date",
		getdate(new_departure),
	)
	resize(stay.room_occupancy)
	redistribute(stay.room_occupancy)
