"""F2 Room inventory engine: counters, locking, rebuild and reconciliation."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from frappoint.vuna_hospitality.report.house_position import house_position
from frappoint.vuna_hospitality.services import inventory
from frappoint.vuna_hospitality.services.inventory import (
	InventoryUnavailableError,
	acquire,
	acquire_many,
	convert,
	ensure_rows,
	nights_between,
	rebuild,
	reconcile,
	release,
)
from frappoint.vuna_hospitality.tests.utils import make_test_property, run_concurrently


def _row(room_type, night):
	return frappe.get_doc("Room Type Inventory Day", inventory.row_name(room_type, night))


class InventoryTestCase(IntegrationTestCase):
	def setUp(self):
		frappe.db.savepoint("inventory_test")
		self.prop, self.rooms = make_test_property(code="INV", room_types={"STD": 3, "DLX": 1})
		self.today = getdate(self.prop.business_date)
		self.std, self.dlx = "INV-STD", "INV-DLX"

	def tearDown(self):
		frappe.db.rollback(save_point="inventory_test")

	def night(self, offset):
		return add_days(self.today, offset)


class TestNightsAndRows(InventoryTestCase):
	def test_nights_are_half_open(self):
		self.assertEqual(nights_between("2026-11-14", "2026-11-16"), [date(2026, 11, 14), date(2026, 11, 15)])
		with self.assertRaises(frappe.ValidationError):
			nights_between("2026-11-16", "2026-11-16")

	def test_rows_are_created_from_rooms(self):
		created = ensure_rows([self.std, self.dlx], [self.night(0), self.night(1)])
		self.assertEqual(created, 4)
		row = _row(self.std, self.night(0))
		self.assertEqual(
			(row.physical_rooms, row.out_of_order, row.sold, row.held, row.available), (3, 0, 0, 0, 3)
		)
		self.assertEqual(row.property, "INV")
		self.assertEqual(ensure_rows([self.std], [self.night(0)]), 0)  # already there

	def test_rows_cannot_be_saved_through_the_document_api(self):
		ensure_rows([self.std], [self.night(0)])
		row = _row(self.std, self.night(0))
		row.sold = 99
		with self.assertRaises(frappe.ValidationError):
			row.save(ignore_permissions=True)


class TestAcquireAndRelease(InventoryTestCase):
	def test_acquire_takes_one_room_every_night(self):
		acquire(self.std, self.night(0), self.night(2))
		self.assertEqual([_row(self.std, self.night(n)).held for n in (0, 1)], [1, 1])
		self.assertEqual(_row(self.std, self.night(0)).available, 2)
		self.assertFalse(
			frappe.db.exists("Room Type Inventory Day", inventory.row_name(self.std, self.night(2)))
		)

	def test_sold_out_names_the_first_full_night_and_changes_nothing(self):
		acquire(self.dlx, self.night(1), self.night(2), kind="sold")  # only DLX room taken on night 1
		with self.assertRaises(InventoryUnavailableError) as raised:
			acquire(self.dlx, self.night(0), self.night(3))
		self.assertEqual(raised.exception.night, self.night(1))
		self.assertEqual(_row(self.dlx, self.night(0)).held, 0)  # night 0 untouched: all or nothing
		self.assertEqual(_row(self.dlx, self.night(2)).held, 0)

	def test_multi_room_booking_is_all_or_nothing(self):
		with self.assertRaises(InventoryUnavailableError):
			acquire_many(
				[
					{"room_type": self.std, "arrival": self.night(0), "departure": self.night(1)},
					{
						"room_type": self.dlx,
						"arrival": self.night(0),
						"departure": self.night(1),
						"quantity": 2,
					},
				]
			)
		self.assertEqual(_row(self.std, self.night(0)).held, 0)

	def test_overbooking_only_when_authorised(self):
		frappe.db.set_value("Room Type", self.dlx, "overbooking_limit", 1)
		acquire(self.dlx, self.night(0), self.night(1), kind="sold")
		with self.assertRaises(InventoryUnavailableError):
			acquire(self.dlx, self.night(0), self.night(1))
		acquire(self.dlx, self.night(0), self.night(1), allow_overbooking=True)
		self.assertEqual(_row(self.dlx, self.night(0)).available, 0)

	def test_release_and_convert(self):
		acquire(self.std, self.night(0), self.night(2), quantity=2)
		convert(self.std, self.night(0), self.night(2), quantity=1)
		row = _row(self.std, self.night(0))
		self.assertEqual((row.held, row.sold, row.available), (1, 1, 1))

		release(self.std, self.night(0), self.night(2), kind="held")
		release(self.std, self.night(0), self.night(2), kind="sold")
		self.assertEqual(_row(self.std, self.night(1)).available, 3)
		with self.assertRaises(frappe.ValidationError):
			release(self.std, self.night(0), self.night(1))  # nothing left to release


class TestSupplyChanges(InventoryTestCase):
	def _period(self, state, start, end, room="INV-101"):
		return frappe.get_doc(
			{
				"doctype": "Room State Period",
				"room": room,
				"state": state,
				"from_date": self.night(start),
				"to_date": self.night(end),
				"reason": "Test",
			}
		).insert()

	def test_out_of_order_period_removes_rooms_for_its_nights_only(self):
		ensure_rows([self.std], [self.night(n) for n in range(4)])
		period = self._period("Out of Order", 1, 3)
		period.submit()
		self.assertEqual([_row(self.std, self.night(n)).available for n in range(4)], [3, 2, 2, 3])
		period.cancel()
		self.assertEqual(_row(self.std, self.night(1)).available, 3)

	def test_out_of_service_stays_in_inventory(self):
		ensure_rows([self.std], [self.night(0)])
		self._period("Out of Service", 0, 1).submit()
		row = _row(self.std, self.night(0))
		self.assertEqual((row.out_of_service, row.available), (1, 3))

	def test_deactivating_a_room_reduces_physical_rooms(self):
		ensure_rows([self.std], [self.night(0)])
		room = frappe.get_doc("Hotel Room", "INV-103")
		room.is_active = 0
		room.save()
		self.assertEqual(_row(self.std, self.night(0)).physical_rooms, 2)

	def test_supply_refresh_keeps_demand(self):
		acquire(self.std, self.night(0), self.night(1))
		self._period("Out of Order", 0, 1).submit()
		row = _row(self.std, self.night(0))
		self.assertEqual((row.held, row.out_of_order, row.available), (1, 1, 1))


class TestRebuildAndReconcile(InventoryTestCase):
	def test_reconcile_reports_and_rebuild_fixes_drift(self):
		ensure_rows([self.std, self.dlx], [self.night(0), self.night(1)])
		self.assertEqual(reconcile("INV", self.night(0), self.night(1)), [])

		frappe.db.set_value(
			"Room Type Inventory Day", inventory.row_name(self.std, self.night(0)), "physical_rooms", 9
		)
		drift = reconcile("INV", self.night(0), self.night(1))
		self.assertEqual(len(drift), 1)
		self.assertEqual(drift[0]["differences"]["physical_rooms"], {"stored": 9, "expected": 3})

		result = rebuild("INV", self.night(0), self.night(1))
		self.assertEqual(result["updated"], 1)
		self.assertEqual(reconcile("INV", self.night(0), self.night(1)), [])

	def test_rebuild_takes_demand_from_registered_sources(self):
		def fake_occupancies(room_types, nights):
			return {(self.std, self.night(0)): {"sold": 2}}

		with patch.object(inventory, "DEMAND_SOURCES", [fake_occupancies]):
			rebuild("INV", self.night(0), self.night(0))
			row = _row(self.std, self.night(0))
			self.assertEqual((row.sold, row.available), (2, 1))
			self.assertEqual(reconcile("INV", self.night(0), self.night(0)), [])

	def test_counters_without_occupancies_show_as_drift(self):
		acquire(self.std, self.night(0), self.night(1), kind="sold")  # no occupancy recorded (F5)
		drift = reconcile("INV", self.night(0), self.night(0))
		self.assertEqual(drift[0]["differences"]["sold"], {"stored": 1, "expected": 0})

	def test_house_position_report(self):
		acquire(self.std, self.night(0), self.night(1))
		columns, data = house_position.execute({"property": "INV", "days": 2, "show_breakdown": 1})
		self.assertEqual(len(columns), 3)  # label + 2 nights
		std = next(row for row in data if row.get("room_type") == self.std and row["indent"] == 0)
		field = house_position.night_field(self.night(0))
		self.assertEqual(std[field], 2)
		held = next(row for row in data if row["parent_key"] == self.std and row["label"] == "Held")
		self.assertEqual(held[field], 1)
		self.assertEqual(data[-1][field], 3)  # total available: 2 STD + 1 DLX


class TestConcurrentSale(IntegrationTestCase):
	"""Scenario 9 (inventory part): two agents race for the last room; exactly one wins."""

	CODE = "RACE"

	def setUp(self):
		self._cleanup()
		self.prop, _rooms = make_test_property(code=self.CODE, room_types={"STD": 1})
		self.arrival = getdate(self.prop.business_date)
		ensure_rows([f"{self.CODE}-STD"], nights_between(self.arrival, add_days(self.arrival, 2)))
		frappe.db.commit()  # the racing connections must see the data

	def tearDown(self):
		self._cleanup()

	def _cleanup(self):
		frappe.db.rollback()
		frappe.db.delete("Room Type Inventory Day", {"property": self.CODE})
		frappe.db.delete("Hotel Room", {"property": self.CODE})
		frappe.db.delete("Room Type", {"property": self.CODE})
		frappe.db.delete("Hotel Property", {"name": self.CODE})
		frappe.db.commit()

	def test_only_one_of_two_concurrent_requests_gets_the_last_room(self):
		room_type, arrival = f"{self.CODE}-STD", self.arrival

		def book_two_nights():
			return acquire(room_type, arrival, add_days(arrival, 2), kind="sold")

		def book_second_night():
			return acquire(room_type, add_days(arrival, 1), add_days(arrival, 2), kind="sold")

		results = run_concurrently(book_two_nights, book_second_night)

		winners = [result for result in results if result.ok]
		losers = [result for result in results if not result.ok]
		self.assertEqual(len(winners), 1, [result.error for result in results])
		self.assertIsInstance(losers[0].error, InventoryUnavailableError)
		self.assertEqual(
			frappe.db.get_value(
				"Room Type Inventory Day", inventory.row_name(room_type, add_days(arrival, 1)), "sold"
			),
			1,
		)
