"""Room inventory engine (design §9.3, §28.4; feature F2).

Room Type Inventory Day holds one row per property, room type and night:

    available = physical_rooms - out_of_order - sold - held - block_unpicked + overbooking_limit

Rules:

- Nights are half-open: arrival 14 Nov, departure 16 Nov uses the nights of 14 and 15.
- Selling and releasing always lock the rows first (SELECT ... FOR UPDATE), ordered by room type
  then night, so two agents can't sell the last room and concurrent bookings can't deadlock.
- The rows are a cache. Supply (rooms, out-of-order periods, overbooking limit) and demand (room
  occupancies, group blocks) are the truth; `rebuild()` recomputes rows from them and
  `reconcile()` reports any row that drifted.

Demand sources arrive with later features: Room Occupancy (F5) and Group Block (Release 2)
register a function in DEMAND_SOURCES that returns their counts per room type and night.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, now_datetime

from frappoint.vuna_hospitality.services.feature_flag import hospitality_job
from frappoint.vuna_hospitality.services.rooms import OUT_OF_ORDER, OUT_OF_SERVICE

DOCTYPE = "Room Type Inventory Day"
HELD, SOLD = "held", "sold"
DEMAND_KINDS = (HELD, SOLD)
SUPPLY_FIELDS = ("physical_rooms", "out_of_order", "out_of_service", "overbooking_limit", "day_use_capacity")
DEMAND_FIELDS = ("held", "sold", "block_unpicked", "day_use_sold")
COUNTER_FIELDS = SUPPLY_FIELDS + DEMAND_FIELDS
AVAILABLE_SQL = "physical_rooms - out_of_order - sold - held - block_unpicked + overbooking_limit"
DEFAULT_HORIZON_DAYS = 365

# Each source: fn(room_types: list[str], nights: list[date]) -> {(room_type, night): {field: count}}
# with fields from DEMAND_FIELDS. Room Occupancy (F5) and Group Block (R2) add theirs here.
DEMAND_SOURCES: list[Callable[[list[str], list[date]], dict]] = []


class InventoryUnavailableError(frappe.ValidationError):
	"""Not enough rooms of a type on a night. `night` and `room_type` say where."""

	def __init__(self, message: str, room_type: str | None = None, night: date | None = None):
		super().__init__(message)
		self.room_type = room_type
		self.night = night


# --------------------------------------------------------------------------- nights


def nights_between(arrival, departure) -> list[date]:
	"""The nights a stay uses: arrival inclusive, departure exclusive."""
	start, end = getdate(arrival), getdate(departure)
	if end <= start:
		frappe.throw(_("Departure must be after arrival."))
	return [start + timedelta(days=offset) for offset in range((end - start).days)]


def row_name(room_type: str, night) -> str:
	return f"{room_type}-{getdate(night)}"


# --------------------------------------------------------------------------- truth


def compute_supply(room_types: Iterable[str], nights: Iterable[date]) -> dict[tuple[str, date], dict]:
	"""Rooms, out-of-order/out-of-service counts and limits per room type and night, from the records."""
	room_types, nights = sorted(set(room_types)), sorted(set(nights))
	if not room_types or not nights:
		return {}

	types = {
		row.name: row
		for row in frappe.get_all(
			"Room Type",
			filters={"name": ["in", room_types]},
			fields=["name", "property", "overbooking_limit", "day_use_capacity", "is_active"],
		)
	}
	physical = defaultdict(int)
	for room_type in frappe.get_all(
		"Hotel Room", filters={"room_type": ["in", room_types], "is_active": 1}, pluck="room_type"
	):
		physical[room_type] += 1

	closed = defaultdict(lambda: {OUT_OF_ORDER: set(), OUT_OF_SERVICE: set()})
	for period in frappe.get_all(
		"Room State Period",
		filters={
			"room_type": ["in", room_types],
			"docstatus": 1,
			"from_date": ["<=", nights[-1]],
			"to_date": [">", nights[0]],
		},
		fields=["room", "room_type", "state", "from_date", "to_date"],
	):
		if not frappe.db.get_value("Hotel Room", period.room, "is_active"):
			continue
		for night in nights_between(max(getdate(period.from_date), nights[0]), period.to_date):
			if night > nights[-1]:
				break
			closed[(period.room_type, night)][period.state].add(period.room)

	supply = {}
	for room_type in room_types:
		room_type_row = types.get(room_type)
		if not room_type_row:
			continue
		active = cint(room_type_row.is_active)
		for night in nights:
			states = closed[(room_type, night)]
			out_of_order = states[OUT_OF_ORDER]
			supply[(room_type, night)] = {
				"property": room_type_row.property,
				"physical_rooms": physical[room_type] if active else 0,
				"out_of_order": len(out_of_order) if active else 0,
				# A room that is both is counted once, as out of order.
				"out_of_service": len(states[OUT_OF_SERVICE] - out_of_order) if active else 0,
				"overbooking_limit": cint(room_type_row.overbooking_limit) if active else 0,
				"day_use_capacity": cint(room_type_row.day_use_capacity) if active else 0,
			}
	return supply


def compute_demand(room_types: Iterable[str], nights: Iterable[date]) -> dict[tuple[str, date], dict]:
	"""Held, sold and blocked counts per room type and night, from every registered demand source."""
	room_types, nights = sorted(set(room_types)), sorted(set(nights))
	demand = defaultdict(lambda: dict.fromkeys(DEMAND_FIELDS, 0))
	for source in DEMAND_SOURCES:
		for key, counts in (source(room_types, nights) or {}).items():
			for field, value in counts.items():
				demand[key][field] += cint(value)
	return demand


def expected_rows(room_types: Iterable[str], nights: Iterable[date]) -> dict[tuple[str, date], dict]:
	"""What every row should contain, computed from the real records."""
	supply = compute_supply(room_types, nights)
	demand = compute_demand(room_types, nights)
	rows = {}
	for key, values in supply.items():
		row = {**values, **demand[key]}
		row["available"] = (
			row["physical_rooms"]
			- row["out_of_order"]
			- row["sold"]
			- row["held"]
			- row["block_unpicked"]
			+ row["overbooking_limit"]
		)
		rows[key] = row
	return rows


# --------------------------------------------------------------------------- rows


def ensure_rows(room_types: Iterable[str], nights: Iterable[date]) -> int:
	"""Create any missing rows from the records. Safe when two requests create the same row."""
	room_types, nights = sorted(set(room_types)), sorted(set(nights))
	if not room_types or not nights:
		return 0
	existing = set(
		frappe.get_all(
			DOCTYPE,
			filters={"room_type": ["in", room_types], "inventory_date": ["between", [nights[0], nights[-1]]]},
			pluck="name",
		)
	)
	missing = [(rt, night) for rt in room_types for night in nights if row_name(rt, night) not in existing]
	if not missing:
		return 0

	expected = expected_rows({rt for rt, _ in missing}, {night for _, night in missing})
	now, user = now_datetime(), frappe.session.user
	fields = [
		"name",
		"owner",
		"modified_by",
		"creation",
		"modified",
		"docstatus",
		"idx",
		"room_type",
		"inventory_date",
		"last_rebuilt_at",
		"available",
		*COUNTER_FIELDS,
		"property",
	]
	values = []
	for room_type, night in missing:
		row = expected.get((room_type, night))
		if not row:
			frappe.throw(_("Room Type {0} does not exist.").format(room_type))
		values.append(
			[row_name(room_type, night), user, user, now, now, 0, 0, room_type, night, now, row["available"]]
			+ [row[field] for field in COUNTER_FIELDS]
			+ [row["property"]]
		)
	# Concurrent requests may insert the same rows; the unique key makes that harmless.
	frappe.db.bulk_insert(DOCTYPE, fields, values, ignore_duplicates=True)
	return len(values)


def lock_rows(room_types: Iterable[str], nights: Iterable[date]) -> dict[tuple[str, date], dict]:
	"""SELECT ... FOR UPDATE the rows, always ordered by room type then night."""
	room_types, nights = sorted(set(room_types)), sorted(set(nights))
	rows = frappe.db.sql(
		f"""
		SELECT name, property, room_type, inventory_date, available, {", ".join(COUNTER_FIELDS)}
		FROM `tab{DOCTYPE}`
		WHERE room_type IN %(room_types)s AND inventory_date IN %(nights)s
		ORDER BY room_type, inventory_date
		FOR UPDATE
		""",
		{"room_types": tuple(room_types), "nights": tuple(nights)},
		as_dict=True,
	)
	return {(row.room_type, getdate(row.inventory_date)): row for row in rows}


# --------------------------------------------------------------------------- acquire / release


def acquire(
	room_type: str,
	arrival,
	departure,
	kind: str = HELD,
	quantity: int = 1,
	allow_overbooking: bool = False,
) -> list[str]:
	"""Take `quantity` rooms of `room_type` for every night of the stay, or none at all.

	Call inside the transaction that also creates the Room Occupancy (F5), so the counters and
	the occupancy commit together. Raises InventoryUnavailableError naming the first night that
	is full. Returns the names of the rows changed.
	"""
	return acquire_many(
		[{"room_type": room_type, "arrival": arrival, "departure": departure, "quantity": quantity}],
		kind=kind,
		allow_overbooking=allow_overbooking,
	)


def acquire_many(requests: list[dict], kind: str = HELD, allow_overbooking: bool = False) -> list[str]:
	"""Acquire several room types at once (a multi-room booking): all succeed or none do."""
	_check_kind(kind)
	needed = _needed_per_row(requests)
	room_types = {room_type for room_type, _ in needed}
	nights = {night for _, night in needed}

	ensure_rows(room_types, nights)
	rows = lock_rows(room_types, nights)

	for room_type, night in sorted(needed):
		row = rows.get((room_type, night))
		free = 0
		if row:
			# Overbooking rooms only count when the caller has authorised overbooking.
			free = row.available if allow_overbooking else row.available - row.overbooking_limit
		if free < needed[(room_type, night)]:
			raise InventoryUnavailableError(
				_("{0} is sold out on {1}.").format(
					frappe.db.get_value("Room Type", room_type, "room_type_name") or room_type,
					frappe.format(night, "Date"),
				),
				room_type=room_type,
				night=night,
			)

	return _apply(needed, rows, {kind: +1})


def release(room_type: str, arrival, departure, kind: str = HELD, quantity: int = 1) -> list[str]:
	"""Give back rooms taken by `acquire` (cancellation, hold expiry, shortened stay)."""
	_check_kind(kind)
	needed = _needed_per_row(
		[{"room_type": room_type, "arrival": arrival, "departure": departure, "quantity": quantity}]
	)
	rows = lock_rows({room_type}, {night for _, night in needed})
	for key, count in sorted(needed.items()):
		row = rows.get(key)
		if not row or row[kind] < count:
			frappe.throw(
				_(
					"Cannot release {0} {1} room(s) for {2} on {3}: only {4} recorded. Run an inventory rebuild."
				).format(count, _(kind), key[0], frappe.format(key[1], "Date"), row[kind] if row else 0)
			)
	return _apply(needed, rows, {kind: -1})


def convert(
	room_type: str, arrival, departure, quantity: int = 1, from_kind: str = HELD, to_kind: str = SOLD
) -> list[str]:
	"""Move rooms from held to sold (confirming a booking) without changing availability."""
	_check_kind(from_kind)
	_check_kind(to_kind)
	needed = _needed_per_row(
		[{"room_type": room_type, "arrival": arrival, "departure": departure, "quantity": quantity}]
	)
	rows = lock_rows({room_type}, {night for _, night in needed})
	for key, count in sorted(needed.items()):
		row = rows.get(key)
		if not row or row[from_kind] < count:
			frappe.throw(
				_("No {0} rooms to convert for {1} on {2}.").format(
					_(from_kind), key[0], frappe.format(key[1], "Date")
				)
			)
	return _apply(needed, rows, {from_kind: -1, to_kind: +1})


def _check_kind(kind: str) -> None:
	if kind not in DEMAND_KINDS:
		frappe.throw(_("Inventory kind must be one of: {0}.").format(", ".join(DEMAND_KINDS)))


def _needed_per_row(requests: list[dict]) -> dict[tuple[str, date], int]:
	needed: dict[tuple[str, date], int] = defaultdict(int)
	for request in requests:
		quantity = cint(request.get("quantity") or 1)
		if quantity < 1:
			frappe.throw(_("Quantity must be at least 1."))
		for night in nights_between(request["arrival"], request["departure"]):
			needed[(request["room_type"], night)] += quantity
	return dict(needed)


def _apply(needed: dict, rows: dict, signs: dict[str, int]) -> list[str]:
	changed = []
	for key in sorted(needed):
		row = rows[key]
		assignments = ", ".join(f"`{field}` = `{field}` + %(delta_{field})s" for field in signs)
		params = {"name": row.name, **{f"delta_{field}": sign * needed[key] for field, sign in signs.items()}}
		frappe.db.sql(
			f"UPDATE `tab{DOCTYPE}` SET {assignments}, `modified` = NOW(6) WHERE name = %(name)s",
			params,
		)
		frappe.db.sql(
			f"UPDATE `tab{DOCTYPE}` SET available = {AVAILABLE_SQL} WHERE name = %(name)s", {"name": row.name}
		)
		changed.append(row.name)
	return changed


# --------------------------------------------------------------------------- rebuild / reconcile


def get_horizon_end(property_name: str) -> date:
	business_date = getdate(frappe.db.get_value("Hotel Property", property_name, "business_date"))
	days = (
		cint(frappe.db.get_single_value("Hospitality Settings", "max_advance_booking_days"))
		or DEFAULT_HORIZON_DAYS
	)
	return add_days(business_date, days)


def property_room_types(property_name: str, room_type: str | None = None) -> list[str]:
	filters = {"property": property_name}
	if room_type:
		filters["name"] = room_type
	return frappe.get_all("Room Type", filters=filters, pluck="name", order_by="name")


def _date_range(property_name: str, from_date=None, to_date=None) -> list[date]:
	start = getdate(from_date or frappe.db.get_value("Hotel Property", property_name, "business_date"))
	end = getdate(to_date or get_horizon_end(property_name))
	return nights_between(start, add_days(end, 1))


def rebuild(property_name: str, from_date=None, to_date=None, room_type: str | None = None) -> dict:
	"""Recompute every row in the range from the records, under lock. Returns counts."""
	room_types = property_room_types(property_name, room_type)
	nights = _date_range(property_name, from_date, to_date)
	created = ensure_rows(room_types, nights)
	rows = lock_rows(room_types, nights)
	expected = expected_rows(room_types, nights)
	updated = 0
	now = now_datetime()
	for key, row in rows.items():
		values = expected.get(key)
		if not values:
			continue
		changes = {
			field: values[field]
			for field in (*COUNTER_FIELDS, "available")
			if row.get(field) != values[field]
		}
		changes["last_rebuilt_at"] = now
		frappe.db.set_value(DOCTYPE, row.name, changes, update_modified=len(changes) > 1)
		updated += len(changes) > 1
	return {"created": created, "updated": updated, "rows": len(rows)}


def refresh_supply(room_types: Iterable[str], from_date=None, to_date=None) -> int:
	"""Recompute only the supply columns of existing rows (rooms or state periods changed).

	Demand columns (held, sold, ...) are left alone, so this is safe before demand sources exist.
	"""
	room_types = sorted({rt for rt in room_types if rt})
	if not room_types:
		return 0
	filters = {"room_type": ["in", room_types]}
	if from_date and to_date:
		filters["inventory_date"] = ["between", [getdate(from_date), getdate(to_date)]]
	elif from_date:
		filters["inventory_date"] = [">=", getdate(from_date)]
	existing = frappe.get_all(DOCTYPE, filters=filters, fields=["room_type", "inventory_date"])
	if not existing:
		return 0
	nights = {getdate(row.inventory_date) for row in existing}
	rows = lock_rows(room_types, nights)
	supply = compute_supply(room_types, nights)
	changed = 0
	for key, row in rows.items():
		values = supply.get(key)
		if not values:
			continue
		changes = {field: values[field] for field in SUPPLY_FIELDS if row.get(field) != values[field]}
		if changes:
			frappe.db.set_value(DOCTYPE, row.name, changes)
			frappe.db.sql(
				f"UPDATE `tab{DOCTYPE}` SET available = {AVAILABLE_SQL} WHERE name = %(name)s",
				{"name": row.name},
			)
			changed += 1
	return changed


def reconcile(property_name: str, from_date=None, to_date=None) -> list[dict]:
	"""Compare stored rows with the records, without changing anything. Returns the drifted rows."""
	room_types = property_room_types(property_name)
	nights = _date_range(property_name, from_date, to_date)
	if not room_types:
		return []
	stored = {
		(row.room_type, getdate(row.inventory_date)): row
		for row in frappe.get_all(
			DOCTYPE,
			filters={"room_type": ["in", room_types], "inventory_date": ["between", [nights[0], nights[-1]]]},
			fields=["name", "room_type", "inventory_date", "available", *COUNTER_FIELDS],
		)
	}
	drift = []
	for key, values in expected_rows(room_types, nights).items():
		row = stored.get(key)
		if not row:
			continue  # not created yet; ensure_rows will compute it correctly
		differences = {
			field: {"stored": row[field], "expected": values[field]}
			for field in (*COUNTER_FIELDS, "available")
			if row[field] != values[field]
		}
		if differences:
			drift.append({"name": row.name, "room_type": key[0], "night": key[1], "differences": differences})
	return drift


def get_availability(property_name: str, from_date, to_date, room_type: str | None = None) -> list[dict]:
	"""Rows for a date range (inclusive), creating any that are missing. Reads only; no locks."""
	room_types = property_room_types(property_name, room_type)
	nights = nights_between(from_date, add_days(to_date, 1))
	ensure_rows(room_types, nights)
	return frappe.get_all(
		DOCTYPE,
		filters={"room_type": ["in", room_types], "inventory_date": ["between", [nights[0], nights[-1]]]},
		fields=["room_type", "inventory_date", "available", *COUNTER_FIELDS],
		order_by="room_type, inventory_date",
	)


# --------------------------------------------------------------------------- jobs and hooks


@hospitality_job
def daily_inventory_maintenance():
	"""Extend each property's rows to its booking horizon, then report any drift."""
	for property_name in frappe.get_all("Hotel Property", filters={"is_active": 1}, pluck="name"):
		ensure_rows(property_room_types(property_name), _date_range(property_name))
		drift = reconcile(property_name)
		if drift:
			report_drift(property_name, drift)
		frappe.db.commit()  # nosemgrep: one property per transaction keeps lock time short


def report_drift(property_name: str, drift: list[dict]) -> None:
	from frappoint.vuna_hospitality.services.event_log import log_event

	sample = [{**row, "night": str(row["night"])} for row in drift[:50]]
	log_event(
		"Hotel Property",
		property_name,
		"Inventory Drift Detected",
		reason=_("{0} inventory row(s) differ from rooms, state periods and occupancies.").format(len(drift)),
		data={"rows": len(drift), "sample": sample},
		property_name=property_name,
	)
	frappe.log_error(
		title=f"Room inventory drift: {property_name}",
		message=frappe.as_json(sample),
		reference_doctype="Hotel Property",
		reference_name=property_name,
	)


def on_rooms_changed(property_name: str, *room_types: str | None) -> int:
	"""A room was added, (de)activated, moved to another type or deleted: refresh those types."""
	return refresh_supply(
		[room_type for room_type in room_types if room_type is not None],
		from_date=_business_date(property_name),
	)


def on_state_period_changed(room_type: str, from_date, to_date) -> int:
	"""A Room State Period was submitted or cancelled: refresh its nights."""
	return refresh_supply([room_type], from_date=from_date, to_date=add_days(to_date, -1))


def _business_date(property_name: str):
	return frappe.db.get_value("Hotel Property", property_name, "business_date")


@frappe.whitelist()
def rebuild_property_inventory(property_name: str) -> dict:
	"""Desk action: rebuild a property's rows from today's business date to its horizon."""
	frappe.only_for(("System Manager", "Hospitality Manager"))
	from frappoint.vuna_hospitality.services.property_scope import assert_property_access

	assert_property_access(property_name)
	result = rebuild(property_name)
	result["drift_after"] = len(reconcile(property_name))
	return result
