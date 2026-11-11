"""F6 Stay guests, room assignment, check-in and check-out."""

from datetime import timedelta

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from frappoint.vuna_hospitality.api.front_desk import get_front_desk_today
from frappoint.vuna_hospitality.services import front_desk, inventory
from frappoint.vuna_hospitality.services.feature_flag import HospitalityDisabledError
from frappoint.vuna_hospitality.services.front_desk import (
	CheckInRefusedError,
	RoomUnavailableError,
	add_stay_guest,
	assign_room,
	check_in,
	check_out,
	move_room,
	register_guest,
	remove_stay_guest,
	set_primary_guest,
	set_room_lock,
)
from frappoint.vuna_hospitality.services.guests import ProvisionalGuestError
from frappoint.vuna_hospitality.services.reservations import cancel, confirm, hold
from frappoint.vuna_hospitality.tests.test_reservations import counters, make_booking_fixtures, stay_request
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled


def make_guest(first_name, code, **fields):
	return frappe.get_doc(
		{"doctype": "Guest Profile", "first_name": first_name, "last_name": f"Test{code}", **fields}
	).insert(ignore_permissions=True)


class FrontDeskTestCase(IntegrationTestCase):
	CODE = "FDK"

	def setUp(self):
		frappe.db.savepoint("front_desk_test")
		self.prop, self.plan, self.guest = make_booking_fixtures(self.CODE, rooms=2)
		self.today = getdate(self.prop.business_date)
		self.room_a, self.room_b = f"{self.CODE}-101", f"{self.CODE}-102"
		frappe.db.set_value("Room Type", f"{self.CODE}-STD", "overbooking_limit", 0)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="front_desk_test")

	def confirmed_stay(self, nights=2, arrival=None, guest=None):
		summary = hold(
			self.CODE,
			[stay_request(self.CODE, self.plan, guest or self.guest, arrival or self.today, nights)],
			booking_details={"booking_source": "Phone"},
		)
		confirm(summary["stays"][0]["name"])
		return frappe.get_doc("Stay Reservation", summary["stays"][0]["name"])

	def guests(self, stay):
		return frappe.get_all(
			"Stay Guest",
			filters={"stay_reservation": stay.name},
			fields=["name", "guest_profile", "role", "status", "age_category"],
			order_by="creation asc",
		)

	def register_all(self, stay):
		for guest in self.guests(stay):
			if guest.status == "Expected" and guest.age_category == "Adult":
				register_guest(guest.name)

	def room(self, room):
		return frappe.db.get_value("Hotel Room", room, ["occupancy_status", "housekeeping_condition"])


class TestCoupleStay(FrontDeskTestCase):
	def test_couple_books_moves_rooms_and_checks_out(self):
		"""Plan F6 done-when: a couple is assigned one room, moves to another, and checks out."""
		stay = self.confirmed_stay(nights=2)
		partner = make_guest("Baraka", self.CODE)
		add_stay_guest(stay.name, partner.name)
		self.assertEqual(
			frappe.db.get_value("Room Occupancy", stay.room_occupancy, ["adults", "children"]), (2, 0)
		)

		assign_room(stay.name, self.room_a)
		self.register_all(stay)
		check_in(stay.name)
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "status"), "In House")
		self.assertEqual({g.status for g in self.guests(stay)}, {"Checked In"})
		self.assertEqual(self.room(self.room_a)[0], "Occupied")

		move_room(stay.name, self.room_b, "Noise")
		self.assertEqual(self.room(self.room_a), ("Vacant", "Dirty"))
		self.assertEqual(self.room(self.room_b)[0], "Occupied")

		check_out(stay.name)
		history = front_desk.stay_details(stay.name)
		self.assertEqual([a["hotel_room"] for a in history["assignments"]], [self.room_a, self.room_b])
		self.assertEqual({a["status"] for a in history["assignments"]}, {"Released"})
		self.assertEqual(history["assignments"][1]["previous_assignment"], history["assignments"][0]["name"])
		self.assertEqual(history["stay"]["status"], "Checked Out")
		self.assertEqual({g["status"] for g in history["guests"]}, {"Checked Out"})
		self.assertEqual(self.room(self.room_b), ("Vacant", "Dirty"))
		self.assertEqual(frappe.db.get_value("Hotel Booking", stay.hotel_booking, "status"), "Closed")
		self.assertIn("Room Moved", [e["event_type"] for e in history["events"]])


class TestStayGuests(FrontDeskTestCase):
	def test_hold_records_the_lead_guest_as_primary(self):
		stay = self.confirmed_stay()
		self.assertEqual(
			[(g.guest_profile, g.role) for g in self.guests(stay)], [(self.guest.name, "Primary")]
		)

	def test_room_capacity_is_enforced(self):
		stay = self.confirmed_stay()
		add_stay_guest(stay.name, make_guest("Second", self.CODE).name)
		add_stay_guest(stay.name, make_guest("Child", self.CODE).name, age_category="Child")
		with self.assertRaises(frappe.ValidationError):
			add_stay_guest(stay.name, make_guest("Third", self.CODE).name)  # STD sleeps 2 adults
		child = next(g for g in self.guests(stay) if g.age_category == "Child")
		self.assertEqual(frappe.db.get_value("Stay Guest", child.name, "guardian"), self.guest.name)

	def test_primary_guest_can_change_but_not_be_removed(self):
		stay = self.confirmed_stay()
		companion = add_stay_guest(stay.name, make_guest("Neema", self.CODE).name)
		primary = next(g.name for g in self.guests(stay) if g.role == "Primary")
		with self.assertRaises(frappe.ValidationError):
			remove_stay_guest(primary, "Not coming")

		set_primary_guest(companion, "Booker is not travelling")
		self.assertEqual(frappe.db.get_value("Stay Guest", companion, "role"), "Primary")
		self.assertEqual(
			frappe.db.get_value("Stay Reservation", stay.name, "lead_guest"),
			frappe.db.get_value("Stay Guest", companion, "guest_profile"),
		)
		remove_stay_guest(primary, "Not coming")
		self.assertEqual(frappe.db.get_value("Stay Guest", primary, "status"), "Removed")

	def test_provisional_guest_must_be_completed_before_registration(self):
		guest = make_guest("Guest of", self.CODE, is_provisional=1)
		stay = self.confirmed_stay(guest=guest)
		primary = self.guests(stay)[0].name
		with self.assertRaises(ProvisionalGuestError):
			register_guest(primary)
		guest.update({"first_name": "Imani", "is_provisional": 0})
		guest.save()
		register_guest(primary)
		self.assertEqual(
			frappe.db.get_value("Stay Guest", primary, ["status", "name_snapshot"]),
			("Registered", f"Imani Test{self.CODE}"),
		)


class TestRoomAssignment(FrontDeskTestCase):
	def test_a_room_is_given_to_one_stay_at_a_time(self):
		first, second = self.confirmed_stay(), self.confirmed_stay()
		assign_room(first.name, self.room_a)
		with self.assertRaises(RoomUnavailableError):
			assign_room(second.name, self.room_a)
		assign_room(second.name, self.room_b)

	def test_back_to_back_stays_respect_turnover_time(self):
		first = self.confirmed_stay(nights=1)
		second = self.confirmed_stay(nights=1, arrival=self.today + timedelta(days=1))
		assign_room(first.name, self.room_a)
		assign_room(second.name, self.room_a)  # 10:00 departure, 14:00 arrival, 60 minutes turnover

		frappe.db.set_value("Hotel Property", self.CODE, "turnover_minutes", 300)
		front_desk.unassign_room(second.name)
		with self.assertRaises(RoomUnavailableError):
			assign_room(second.name, self.room_a)  # five hours of turnover no longer fit

	def test_reassigning_replaces_the_room_unless_locked(self):
		stay = self.confirmed_stay()
		first = assign_room(stay.name, self.room_a)
		assign_room(stay.name, self.room_b)
		self.assertEqual(frappe.db.get_value("Room Assignment", first, "status"), "Cancelled")

		set_room_lock(stay.name, True, "VIP asked for this room")
		with self.assertRaises(frappe.ValidationError):
			assign_room(stay.name, self.room_a)

	def test_cancelling_a_stay_frees_its_room(self):
		stay = self.confirmed_stay()
		assignment = assign_room(stay.name, self.room_a)
		cancel(stay.name, "Trip off")
		self.assertEqual(frappe.db.get_value("Room Assignment", assignment, "status"), "Cancelled")
		assign_room(self.confirmed_stay().name, self.room_a)

	def test_assignable_rooms_show_what_is_free(self):
		first, second = self.confirmed_stay(), self.confirmed_stay()
		assign_room(first.name, self.room_a)
		rooms = {r["name"]: r for r in front_desk.get_assignable_rooms(second.name)}
		self.assertFalse(rooms[self.room_a]["available"])
		self.assertTrue(rooms[self.room_b]["available"])
		self.assertTrue(rooms[self.room_b]["ready"])


class TestCheckInAndOut(FrontDeskTestCase):
	def test_check_in_needs_a_ready_room_and_registered_adults(self):
		stay = self.confirmed_stay()
		with self.assertRaises(CheckInRefusedError):
			check_in(stay.name)  # no room
		assign_room(stay.name, self.room_a)
		with self.assertRaises(CheckInRefusedError):
			check_in(stay.name)  # lead guest not registered
		self.register_all(stay)
		frappe.db.set_value("Hotel Room", self.room_a, "housekeeping_condition", "Dirty")
		with self.assertRaises(CheckInRefusedError):
			check_in(stay.name)  # room not ready
		frappe.db.set_value("Hotel Room", self.room_a, "housekeeping_condition", "Inspected")
		check_in(stay.name)

	def test_no_check_in_before_the_arrival_date(self):
		stay = self.confirmed_stay(arrival=self.today + timedelta(days=2))
		self.register_all(stay)
		with self.assertRaises(CheckInRefusedError):
			check_in(stay.name, self.room_a)

	def test_early_departure_returns_the_remaining_nights(self):
		stay = self.confirmed_stay(nights=3)
		self.register_all(stay)
		check_in(stay.name, self.room_a)
		frappe.db.set_value("Hotel Property", self.CODE, "business_date", self.today + timedelta(days=1))

		check_out(stay.name)
		stay.reload()
		self.assertEqual((getdate(stay.departure_date), stay.nights), (self.today + timedelta(days=1), 1))
		self.assertEqual(counters(self.CODE, self.today)[:2], (0, 1))
		self.assertEqual(counters(self.CODE, self.today + timedelta(days=1))[:2], (0, 0))
		posting = frappe.get_all(
			"Stay Rate Night",
			filters={"stay_reservation": stay.name},
			pluck="posting_state",
			order_by="night_date",
		)
		self.assertEqual(posting, ["Pending", "Cancelled", "Cancelled"])
		self.assertEqual(
			stay.total_amount,
			frappe.db.get_value(
				"Stay Rate Night", {"stay_reservation": stay.name, "night_date": self.today}, "total"
			),
		)
		self.assertEqual(inventory.reconcile(self.CODE), [])

	def test_front_desk_today_lists_arrivals_then_in_house(self):
		stay = self.confirmed_stay()
		self.register_all(stay)
		with hospitality_enabled(True):
			today = get_front_desk_today(self.CODE)
			self.assertEqual([s.name for s in today["arrivals"]], [stay.name])
			check_in(stay.name, self.room_a)
			today = get_front_desk_today(self.CODE)
		self.assertEqual(today["arrivals"], [])
		self.assertEqual([(s.name, s.room_number) for s in today["in_house"]], [(stay.name, "101")])
		with hospitality_enabled(False), self.assertRaises(HospitalityDisabledError):
			get_front_desk_today(self.CODE)
