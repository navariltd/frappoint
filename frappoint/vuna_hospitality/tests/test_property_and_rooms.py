"""F1 Property and rooms: naming, validation, room states, and property isolation."""

from datetime import datetime
from zoneinfo import ZoneInfo

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days

from frappoint.vuna_hospitality.services.rooms import (
	get_sellability,
	refresh_room_sellability,
	set_housekeeping_condition,
)
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled, make_test_property


class RollbackEachTest(IntegrationTestCase):
	"""Undo each test's records, so every test (and its setUp) starts from the same state."""

	def setUp(self):
		frappe.db.savepoint("hospitality_test")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="hospitality_test")


class TestHotelProperty(RollbackEachTest):
	def test_code_is_normalized_and_becomes_the_name(self):
		prop, _rooms = make_test_property(code=" nbo1 ", room_types={"STD": 1})
		self.assertEqual(prop.name, "NBO1")
		self.assertEqual(prop.property_code, "NBO1")

	def test_business_date_starts_as_today_in_the_property_time_zone(self):
		prop, _rooms = make_test_property(code="TZ1", room_types={"STD": 1}, time_zone="Pacific/Kiritimati")
		self.assertEqual(str(prop.business_date), str(datetime.now(ZoneInfo("Pacific/Kiritimati")).date()))

	def test_business_date_cannot_be_edited(self):
		prop, _rooms = make_test_property(code="BD1", room_types={"STD": 1})
		prop.business_date = add_days(prop.business_date, 1)
		with self.assertRaises(frappe.ValidationError):
			prop.save()

	def test_business_date_can_move_with_night_audit_flag(self):
		prop, _rooms = make_test_property(code="BD2", room_types={"STD": 1})
		prop.business_date = add_days(prop.business_date, 1)
		prop.flags.allow_business_date_change = True
		prop.save()

	def test_invalid_code_and_time_zone_are_refused(self):
		with self.assertRaises(frappe.ValidationError):
			make_test_property(code="X", room_types={})
		with self.assertRaises(frappe.ValidationError):
			make_test_property(code="TZ2", room_types={}, time_zone="Mars/Olympus")

	def test_day_use_window_must_be_in_order(self):
		prop, _rooms = make_test_property(code="DU1", room_types={})
		prop.day_use_start, prop.day_use_end = "18:00:00", "10:00:00"
		with self.assertRaises(frappe.ValidationError):
			prop.save()


class TestRoomTypeAndRoom(RollbackEachTest):
	def setUp(self):
		super().setUp()
		self.prop, self.rooms = make_test_property(code="RM1", room_types={"STD": 3, "DLX": 2})

	def test_names_carry_the_property(self):
		self.assertEqual(self.rooms["STD"], ["RM1-101", "RM1-102", "RM1-103"])
		self.assertEqual(self.rooms["DLX"], ["RM1-201", "RM1-202"])
		self.assertEqual(frappe.db.get_value("Hotel Room", "RM1-201", "room_type"), "RM1-DLX")

	def test_room_numbers_are_unique_per_property(self):
		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc(
				{"doctype": "Hotel Room", "property": "RM1", "room_number": "101", "room_type": "RM1-STD"}
			).insert()
		other, other_rooms = make_test_property(code="RM2", room_types={"STD": 1})
		self.assertEqual(other_rooms["STD"], ["RM2-101"])

	def test_room_type_capacity_rules(self):
		room_type = frappe.get_doc("Room Type", "RM1-STD")
		room_type.base_adults = 3
		with self.assertRaises(frappe.ValidationError):
			room_type.save()

	def test_room_count_follows_rooms(self):
		self.assertEqual(frappe.db.get_value("Room Type", "RM1-STD", "room_count"), 3)
		room = frappe.get_doc("Hotel Room", "RM1-103")
		room.is_active = 0
		room.save()
		self.assertEqual(frappe.db.get_value("Room Type", "RM1-STD", "room_count"), 2)

	def test_room_type_must_belong_to_the_same_property(self):
		make_test_property(code="RM3", room_types={"STD": 1})
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{"doctype": "Hotel Room", "property": "RM1", "room_number": "999", "room_type": "RM3-STD"}
			).insert()

	def test_connecting_rooms_link_both_ways(self):
		room = frappe.get_doc("Hotel Room", "RM1-101")
		room.connecting_room = "RM1-102"
		room.save()
		self.assertEqual(frappe.db.get_value("Hotel Room", "RM1-102", "connecting_room"), "RM1-101")

		room.reload()
		room.connecting_room = None
		room.save()
		self.assertIsNone(frappe.db.get_value("Hotel Room", "RM1-102", "connecting_room"))

	def test_state_fields_cannot_be_edited_directly(self):
		room = frappe.get_doc("Hotel Room", "RM1-101")
		room.housekeeping_condition = "Dirty"
		with self.assertRaises(frappe.ValidationError):
			room.save()

	def test_set_housekeeping_condition_command(self):
		with hospitality_enabled(True):
			result = set_housekeeping_condition("RM1-101", "Dirty", reason="Checked out")
		self.assertTrue(result["changed"])
		self.assertEqual(frappe.db.get_value("Hotel Room", "RM1-101", "housekeeping_condition"), "Dirty")
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log",
				{"reference_name": "RM1-101", "to_status": "Dirty", "property": "RM1"},
			)
		)
		with hospitality_enabled(True), self.assertRaises(frappe.ValidationError):
			set_housekeeping_condition("RM1-101", "Sparkling")


class TestRoomStatePeriod(RollbackEachTest):
	def setUp(self):
		super().setUp()
		self.prop, self.rooms = make_test_property(code="OOO", room_types={"STD": 2})
		self.today = self.prop.business_date

	def _period(self, state="Out of Order", start=0, end=3, room="OOO-101", submit=True):
		doc = frappe.get_doc(
			{
				"doctype": "Room State Period",
				"room": room,
				"state": state,
				"from_date": add_days(self.today, start),
				"to_date": add_days(self.today, end),
				"reason": "Broken air conditioning",
			}
		).insert()
		if submit:
			doc.submit()
		return doc

	def test_nights_and_inventory_flag(self):
		period = self._period(submit=False)
		self.assertEqual(period.nights, 3)
		self.assertEqual(period.affects_inventory, 1)
		self.assertEqual(period.property, "OOO")
		self.assertEqual(
			self._period(state="Out of Service", start=5, end=6, submit=False).affects_inventory, 0
		)

	def test_submit_and_cancel_change_sellability(self):
		period = self._period()
		self.assertEqual(frappe.db.get_value("Hotel Room", "OOO-101", "sellability"), "Out of Order")
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log", {"reference_name": "OOO-101", "to_status": "Out of Order"}
			)
		)
		period.cancel()
		self.assertEqual(frappe.db.get_value("Hotel Room", "OOO-101", "sellability"), "Sellable")

	def test_future_period_does_not_affect_today(self):
		self._period(start=2, end=4)
		self.assertEqual(frappe.db.get_value("Hotel Room", "OOO-101", "sellability"), "Sellable")
		self.assertEqual(get_sellability("OOO-101", add_days(self.today, 2)), "Out of Order")
		self.assertEqual(get_sellability("OOO-101", add_days(self.today, 4)), "Sellable")  # back in service

	def test_out_of_order_beats_out_of_service(self):
		self._period(state="Out of Service", start=0, end=1, room="OOO-102")
		self.assertEqual(refresh_room_sellability("OOO-102"), "Out of Service")

	def test_overlapping_periods_are_refused(self):
		self._period(start=0, end=3)
		with self.assertRaises(frappe.ValidationError):
			self._period(state="Out of Service", start=2, end=5, submit=False)
		self._period(start=3, end=4, submit=False)  # starts the day the first one ends: no overlap

	def test_dates_must_be_in_order(self):
		with self.assertRaises(frappe.ValidationError):
			self._period(start=3, end=3, submit=False)


class TestPropertyIsolation(RollbackEachTest):
	"""Scenario 16 (first part): a user restricted to one property only sees that property's rooms."""

	def setUp(self):
		super().setUp()
		make_test_property(code="ISA", room_types={"STD": 2})
		make_test_property(code="ISB", room_types={"STD": 2})
		self.user = "frappoint-isolation@example.com"
		if not frappe.db.exists("User", self.user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": self.user,
					"first_name": "Isolation",
					"send_welcome_email": 0,
					"roles": [{"role": "Front Desk Agent"}],
				}
			).insert(ignore_permissions=True)
		frappe.get_doc(
			{"doctype": "User Permission", "user": self.user, "allow": "Hotel Property", "for_value": "ISA"}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=self.user)

	def test_lists_show_only_permitted_property(self):
		frappe.set_user(self.user)
		rooms = frappe.get_list("Hotel Room", filters={"property": ["in", ["ISA", "ISB"]]}, pluck="name")
		self.assertEqual(sorted(rooms), ["ISA-101", "ISA-102"])
		self.assertEqual(
			frappe.get_list("Hotel Property", filters={"name": ["in", ["ISA", "ISB"]]}, pluck="name"), ["ISA"]
		)

	def test_other_property_room_is_not_readable(self):
		frappe.set_user(self.user)
		self.assertTrue(frappe.has_permission("Hotel Room", "read", "ISA-101"))
		self.assertFalse(frappe.has_permission("Hotel Room", "read", "ISB-101"))
