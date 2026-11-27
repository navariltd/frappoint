"""Amending a stay before arrival: dates, room type, rate plan and guests."""

from datetime import timedelta

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from frappoint.vuna_hospitality.services import amendments, inventory
from frappoint.vuna_hospitality.services.front_desk import assign_room, check_in, register_guest
from frappoint.vuna_hospitality.services.rates import generate_from_season
from frappoint.vuna_hospitality.services.reservations import confirm, hold
from frappoint.vuna_hospitality.tests.utils import (
	make_test_property,
	make_test_rate_setup,
	make_test_season,
)

CODE = "AMD"


def counter(room_type, night, field="sold"):
	return frappe.db.get_value(
		"Room Type Inventory Day", inventory.row_name(f"{CODE}-{room_type}", night), field
	)


class AmendmentTestCase(IntegrationTestCase):
	def setUp(self):
		frappe.db.savepoint("amendment_test")
		self.prop, _rooms = make_test_property(code=CODE, room_types={"STD": 2, "DLX": 1})
		self.plan = make_test_rate_setup(CODE)
		self.today = getdate(self.prop.business_date)
		generate_from_season(
			make_test_season(
				self.plan,
				self.today,
				self.today + timedelta(days=29),
				{f"{CODE}-STD": (10000, 10000), f"{CODE}-DLX": (15000, 15000)},
			).name
		)
		if not frappe.db.exists("UTM Source", "Phone Calls"):
			frappe.get_doc({"doctype": "UTM Source", "name": "Phone Calls"}).insert(ignore_permissions=True)
		self.guest = frappe.get_doc(
			{"doctype": "Guest Profile", "first_name": "Zuri", "last_name": f"Test{CODE}"}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="amendment_test")

	def stay(self, arrival=None, nights=2, room_type="STD", confirmed=True, adults=2):
		arrival = arrival or self.today
		summary = hold(
			CODE,
			[
				{
					"room_type": f"{CODE}-{room_type}",
					"rate_plan": self.plan.name,
					"arrival": arrival,
					"departure": arrival + timedelta(days=nights),
					"lead_guest": self.guest.name,
					"adults": adults,
				}
			],
			booking_details={"booking_source": "Phone Calls"},
		)
		name = summary["stays"][0]["name"]
		if confirmed:
			confirm(name)
		return frappe.get_doc("Stay Reservation", name)

	def nights(self, stay, state="Pending"):
		return frappe.get_all(
			"Stay Rate Night",
			filters={"stay_reservation": stay.name, "posting_state": state},
			pluck="night_date",
			order_by="night_date asc",
		)


class TestAmendments(AmendmentTestCase):
	def test_new_dates_move_the_rooms_and_the_price(self):
		stay = self.stay(arrival=self.today + timedelta(days=1), nights=2)
		new_arrival = self.today + timedelta(days=5)
		result = amendments.amend_stay(
			stay.name, arrival=new_arrival, departure=new_arrival + timedelta(days=3)
		)
		stay.reload()

		self.assertEqual(
			(stay.arrival_date, stay.departure_date, stay.nights),
			(new_arrival, new_arrival + timedelta(days=3), 3),
		)
		self.assertEqual(stay.total_amount, 30000)
		self.assertEqual(self.nights(stay), [new_arrival + timedelta(days=offset) for offset in range(3)])
		# The old nights are given back; the new ones sold.
		self.assertEqual(counter("STD", self.today + timedelta(days=1)), 0)
		self.assertEqual(counter("STD", new_arrival), 1)
		self.assertEqual(result["before"]["arrival_date"], self.today + timedelta(days=1))
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log", {"reference_name": stay.name, "event_type": "Stay Amended"}
			)
		)

	def test_a_full_room_type_refuses_and_nothing_changes(self):
		self.stay(room_type="DLX")  # the only deluxe room
		stay = self.stay()
		frappe.db.savepoint("before_amend")
		with self.assertRaises(inventory.InventoryUnavailableError):
			amendments.amend_stay(stay.name, room_type=f"{CODE}-DLX")
		# The request rolls back, as the API's does: the stay keeps its standard room.
		frappe.db.rollback(save_point="before_amend")
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "room_type"), f"{CODE}-STD")
		self.assertEqual(counter("STD", self.today), 1)

	def test_room_type_upgrade_reprices_and_takes_the_room_off(self):
		stay = self.stay()
		assign_room(stay.name, f"{CODE}-101")
		result = amendments.amend_stay(stay.name, room_type=f"{CODE}-DLX")
		stay.reload()
		self.assertEqual((stay.room_type, stay.total_amount), (f"{CODE}-DLX", 30000))
		self.assertFalse(result["room_kept"])
		self.assertFalse(
			frappe.db.exists(
				"Room Assignment", {"stay_reservation": stay.name, "status": ["in", ("Assigned", "Occupied")]}
			)
		)
		self.assertEqual((counter("STD", self.today), counter("DLX", self.today)), (0, 1))

	def test_a_room_that_still_fits_is_kept_for_the_new_dates(self):
		stay = self.stay(nights=2)
		assign_room(stay.name, f"{CODE}-101")
		result = amendments.amend_stay(stay.name, departure=self.today + timedelta(days=4))
		self.assertTrue(result["room_kept"])
		assignment = frappe.get_value(
			"Room Assignment",
			{"stay_reservation": stay.name, "status": "Assigned"},
			["hotel_room", "end_date"],
			as_dict=True,
		)
		self.assertEqual(
			(assignment.hotel_room, assignment.end_date), (f"{CODE}-101", self.today + timedelta(days=4))
		)

	def test_guests_and_status_are_checked(self):
		stay = self.stay(adults=2)
		with self.assertRaises(amendments.AmendmentError):
			amendments.amend_stay(stay.name)  # nothing to change
		with self.assertRaises(amendments.AmendmentError):
			amendments.amend_stay(stay.name, adults=0)
		amendments.amend_stay(stay.name, adults=1)
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "adults"), 1)

		assign_room(stay.name, f"{CODE}-102")
		for guest in frappe.get_all("Stay Guest", filters={"stay_reservation": stay.name}, pluck="name"):
			register_guest(guest)
		check_in(stay.name)
		with self.assertRaises(amendments.AmendmentError):
			amendments.amend_stay(stay.name, departure=self.today + timedelta(days=5))

	def test_a_held_stay_keeps_its_rooms_held(self):
		stay = self.stay(confirmed=False)
		amendments.amend_stay(stay.name, departure=self.today + timedelta(days=3))
		self.assertEqual(
			(counter("STD", self.today, "held"), counter("STD", self.today + timedelta(days=2), "held")),
			(1, 1),
		)
		self.assertEqual(counter("STD", self.today, "sold"), 0)
