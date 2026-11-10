"""Shared test helpers for hospitality features.

- `hospitality_enabled(state)`: run a block with the module switched on or off.
- `run_concurrently(*fns)`: run functions at the same time on separate database connections,
  to prove locking (for example, that two bookings can't take the last room).
"""

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import frappe

from frappoint.vuna_hospitality.constants import SETTINGS_DOCTYPE


@contextmanager
def hospitality_enabled(state: bool = True) -> Iterator[None]:
	"""Set `enable_hospitality` for the duration of the block, then restore it."""
	previous = frappe.db.get_single_value(SETTINGS_DOCTYPE, "enable_hospitality")
	_set_flag(int(state))
	try:
		yield
	finally:
		_set_flag(previous or 0)


def _set_flag(value: int) -> None:
	# Write directly (no on_update side effects) and drop the per-request value cache that
	# `is_hospitality_enabled()` reads from.
	frappe.db.set_single_value(SETTINGS_DOCTYPE, "enable_hospitality", value)
	frappe.db.value_cache.pop(SETTINGS_DOCTYPE, None)
	frappe.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)


@dataclass
class ConcurrentResult:
	value: Any = None
	error: BaseException | None = None

	@property
	def ok(self) -> bool:
		return self.error is None


def run_concurrently(
	*fns: Callable[[], Any],
	user: str = "Administrator",
	start_timeout: float = 10,
	commit: bool = True,
) -> list[ConcurrentResult]:
	"""Run each function in its own thread with its own Frappe site connection.

	All threads connect first, then start together, so their transactions genuinely overlap.
	Each thread commits on success (unless `commit=False`) and rolls back on error. Errors are
	returned in the result, not raised, so a test can assert exactly one winner.

	Data the functions need must be committed beforehand, because the other connections can't see
	the test's uncommitted transaction. Clean it up afterwards.
	"""
	site = frappe.local.site
	sites_path = frappe.local.sites_path
	results = [ConcurrentResult() for _ in fns]
	ready = threading.Barrier(len(fns))

	def worker(index: int, fn: Callable[[], Any]) -> None:
		frappe.init(site=site, sites_path=sites_path)
		try:
			frappe.connect()
			frappe.set_user(user)
			ready.wait(timeout=start_timeout)
			results[index].value = fn()
			if commit:
				frappe.db.commit()
			else:
				frappe.db.rollback()
		except BaseException as error:
			results[index].error = error
			if getattr(frappe.local, "db", None):
				frappe.db.rollback()
		finally:
			frappe.destroy()

	threads = [threading.Thread(target=worker, args=(i, fn), daemon=True) for i, fn in enumerate(fns)]
	for thread in threads:
		thread.start()
	for thread in threads:
		thread.join(timeout=start_timeout + 60)
	return results


def make_test_property(
	code: str = "TST",
	room_types: dict[str, int] | None = None,
	company: str | None = None,
	time_zone: str = "Africa/Nairobi",
):
	"""Create a small hotel for tests: a property, room types, and numbered rooms.

	`room_types` maps a room-type code to its number of rooms (default STD: 3, DLX: 2). Rooms are
	numbered 101, 102, ... per type block (100s for the first type, 200s for the second, ...).
	Returns (property_doc, {room_type_code: [room names]}). Nothing is committed.
	"""
	room_types = room_types or {"STD": 3, "DLX": 2}
	company = company or frappe.db.get_value("Company", {}, "name")
	prop = frappe.get_doc(
		{
			"doctype": "Hotel Property",
			"property_name": f"Test Hotel {code}",
			"property_code": code,
			"company": company,
			"time_zone": time_zone,
			"check_in_time": "14:00:00",
			"check_out_time": "10:00:00",
		}
	).insert(ignore_permissions=True)

	rooms: dict[str, list[str]] = {}
	for block, (type_code, count) in enumerate(room_types.items(), start=1):
		room_type = frappe.get_doc(
			{
				"doctype": "Room Type",
				"property": prop.name,
				"room_type_name": f"{type_code} Room",
				"code": type_code,
				"base_adults": 2,
				"max_adults": 2,
				"max_children": 1,
				"max_occupancy": 3,
			}
		).insert(ignore_permissions=True)
		rooms[type_code] = [
			frappe.get_doc(
				{
					"doctype": "Hotel Room",
					"property": prop.name,
					"room_number": str(block * 100 + number),
					"room_type": room_type.name,
					"floor": block,
				}
			)
			.insert(ignore_permissions=True)
			.name
			for number in range(1, count + 1)
		]
	return prop, rooms


def make_test_rate_setup(property_name: str, code: str = "BAR"):
	"""Create what a rate plan needs (charge department, room charge code with an Item, cancellation
	and deposit policies) and a nightly rate plan. Returns the Rate Plan document. Nothing is committed.
	"""
	if not frappe.db.exists("Charge Department", "Rooms"):
		frappe.get_doc({"doctype": "Charge Department", "department_name": "Rooms"}).insert(
			ignore_permissions=True
		)

	item_code = "HSP-TEST-ROOM-NIGHT"
	if not frappe.db.exists("Item", item_code):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": "Test Room Night",
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups",
				"stock_uom": frappe.db.get_value("UOM", {}, "name")
				if not frappe.db.exists("UOM", "Nos")
				else "Nos",
				"is_stock_item": 0,
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Charge Code", "TROOM"):
		frappe.get_doc(
			{
				"doctype": "Charge Code",
				"code": "TROOM",
				"description": "Test Room Charge",
				"charge_department": "Rooms",
				"transaction_type": "Revenue",
				"item": item_code,
				"is_room_revenue": 1,
				"print_group": "Accommodation",
			}
		).insert(ignore_permissions=True)

	policies = {}
	for policy_type in ("Cancellation", "Deposit"):
		policies[policy_type] = (
			frappe.get_doc(
				{
					"doctype": "Hotel Policy",
					"property": property_name,
					"policy_name": f"Test {policy_type}",
					"policy_type": policy_type,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	return frappe.get_doc(
		{
			"doctype": "Rate Plan",
			"property": property_name,
			"rate_plan_name": "Best Available Rate",
			"rate_plan_code": code,
			"room_charge_code": "TROOM",
			"cancellation_policy": policies["Cancellation"],
			"deposit_policy": policies["Deposit"],
		}
	).insert(ignore_permissions=True)


def make_test_season(rate_plan, from_date, to_date, rates: dict[str, tuple[float, float | None]]):
	"""A Rate Season for `rate_plan`. `rates` maps room type name -> (weekday rate, weekend rate)."""
	return frappe.get_doc(
		{
			"doctype": "Rate Season",
			"property": rate_plan.property,
			"season_name": "Test Season",
			"rate_plan": rate_plan.name,
			"from_date": from_date,
			"to_date": to_date,
			"rates": [
				{"room_type": room_type, "weekday_rate": weekday, "weekend_rate": weekend}
				for room_type, (weekday, weekend) in rates.items()
			],
		}
	).insert(ignore_permissions=True)
