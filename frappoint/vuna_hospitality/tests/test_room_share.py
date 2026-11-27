"""Independent sharers: stays that share one room, each with its own dates and bill (R2-1)."""

from datetime import timedelta

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, getdate

from frappoint.vuna_hospitality.services import hotel_reports, inventory, night_audit, room_share
from frappoint.vuna_hospitality.services.front_desk import assign_room, check_in, check_out, register_guest
from frappoint.vuna_hospitality.services.rates import generate_from_season
from frappoint.vuna_hospitality.services.reservations import cancel, confirm, hold
from frappoint.vuna_hospitality.tests.utils import (
	make_test_property,
	make_test_rate_setup,
	make_test_season,
)

CODE = "SHR"
ROOM_TYPE = f"{CODE}-STD"


def sold(night):
	return frappe.db.get_value("Room Type Inventory Day", inventory.row_name(ROOM_TYPE, night), "sold")


class RoomShareTestCase(IntegrationTestCase):
	def setUp(self):
		frappe.db.savepoint("room_share_test")
		self.prop, _rooms = make_test_property(code=CODE, room_types={"STD": 3})
		self.plan = make_test_rate_setup(CODE)
		self.today = getdate(self.prop.business_date)
		generate_from_season(
			make_test_season(
				self.plan, self.today, self.today + timedelta(days=29), {ROOM_TYPE: (10000, 10000)}
			).name
		)
		if not frappe.db.exists("UTM Source", "Phone Calls"):
			frappe.get_doc({"doctype": "UTM Source", "name": "Phone Calls"}).insert(ignore_permissions=True)
		frappe.db.set_single_value("Hospitality Settings", "allow_independent_room_share", 1)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="room_share_test")

	def stay(self, first_name, arrival=None, nights=2, adults=1):
		arrival = arrival or self.today
		guest = frappe.get_doc(
			{"doctype": "Guest Profile", "first_name": first_name, "last_name": f"Test{CODE}"}
		).insert(ignore_permissions=True)
		summary = hold(
			CODE,
			[
				{
					"room_type": ROOM_TYPE,
					"rate_plan": self.plan.name,
					"arrival": arrival,
					"departure": arrival + timedelta(days=nights),
					"lead_guest": guest.name,
					"adults": adults,
				}
			],
			booking_details={"booking_source": "Phone Calls"},
		)
		name = summary["stays"][0]["name"]
		confirm(name)
		return frappe.get_doc("Stay Reservation", name)

	def rooms(self, stay):
		"""{night: room component} of the stay's live nights."""
		rows = frappe.get_all(
			"Stay Rate Night",
			filters={"stay_reservation": stay.name, "posting_state": ["!=", "Cancelled"]},
			fields=["night_date", "room_rate", "total"],
			order_by="night_date asc",
		)
		return {getdate(row.night_date): flt(row.room_rate) for row in rows}

	def arrive(self, stay, room=None):
		if room:
			assign_room(stay.name, f"{CODE}-{room}")
		for guest in frappe.get_all("Stay Guest", filters={"stay_reservation": stay.name}, pluck="name"):
			register_guest(guest)
		check_in(stay.name)
		return frappe.get_doc("Stay Reservation", stay.name)

	def post_tonight(self, stay):
		night = frappe.get_all(
			"Stay Rate Night",
			filters={"stay_reservation": stay.name, "night_date": self.today},
			pluck="name",
		)[0]
		night_audit.post_room_night(night, self.today)

	def room_posted(self, stay):
		return sum(
			flt(amount)
			for amount in frappe.get_all(
				"Folio Transaction",
				filters={"stay_reservation": stay.name, "is_room_revenue": 1, "docstatus": 1},
				pluck="net_amount",
			)
		)


class TestRoomShare(RoomShareTestCase):
	def test_the_setting_switches_new_shares_off(self):
		frappe.db.set_single_value("Hospitality Settings", "allow_independent_room_share", 0)
		host, sharer = self.stay("Amani"), self.stay("Baraka")
		with self.assertRaises(room_share.ShareError):
			room_share.join(sharer.name, host.name)
		self.assertFalse(room_share.summary(sharer.name)["can_join"])

	def test_a_couple_with_separate_bills_split_the_room_exactly(self):
		"""Scenario 3: one room counted once, the room charge split 50/50 on separate bills."""
		host, sharer = self.stay("Amani"), self.stay("Baraka")
		self.assertEqual(sold(self.today), 2)
		occupancy = room_share.join(sharer.name, host.name, room_share.EQUAL)

		self.assertEqual(frappe.db.get_value("Stay Reservation", sharer.name, "room_occupancy"), occupancy)
		self.assertEqual(sold(self.today), 1)  # the room is counted once
		self.assertEqual(sold(self.today + timedelta(days=1)), 1)
		self.assertEqual(self.rooms(host), {self.today: 5000, self.today + timedelta(days=1): 5000})
		self.assertEqual(self.rooms(sharer), {self.today: 5000, self.today + timedelta(days=1): 5000})
		self.assertEqual(frappe.db.get_value("Stay Reservation", sharer.name, "total_amount"), 10000)
		self.assertEqual(
			frappe.db.get_value(
				"Occupancy Membership",
				{"stay_reservation": sharer.name, "room_occupancy": occupancy},
				"reason",
			),
			"Join",
		)

		host = self.arrive(host, room="101")
		sharer = self.arrive(sharer)  # moves into the room already in use
		self.assertEqual(sharer.status, "In House")
		self.post_tonight(host)
		self.post_tonight(sharer)
		self.assertEqual((self.room_posted(host), self.room_posted(sharer)), (5000, 5000))
		# Each has its own folio.
		self.assertNotEqual(host.default_folio, sharer.default_folio)
		self.assertEqual(hotel_reports.rooms_sold(CODE, self.today, self.today)[self.today]["paid"], 1)

	def test_the_room_tax_is_split_exactly(self):
		"""Each part's tax is its share of the room's tax, so the parts add up to the room's tax."""
		from frappoint.vuna_hospitality.services import taxes
		from frappoint.vuna_hospitality.tests.test_pricing_packages import make_tax_template

		template = make_tax_template(
			self.prop.company, "HSP Test VAT", {"HSP Test VAT": 16, "HSP Test Levy": 2}
		)
		frappe.db.set_value(
			"Hotel Property", CODE, {"sales_taxes_template": template, "prices_include_tax": 1}
		)
		host, sharer = self.stay("Amani"), self.stay("Baraka")
		room_share.join(sharer.name, host.name, room_share.PERCENTAGE, percent=33.33)
		host, sharer = self.arrive(host, room="101"), self.arrive(sharer)
		self.post_tonight(host)
		self.post_tonight(sharer)

		lines = frappe.get_all(
			"Folio Transaction",
			filters={"stay_reservation": ["in", [host.name, sharer.name]], "is_room_revenue": 1},
			fields=["stay_reservation", "gross_amount", "tax_amount", "tax_breakdown"],
		)
		gross = {line.stay_reservation: flt(line.gross_amount) for line in lines}
		self.assertEqual(gross, {host.name: 3333, sharer.name: 6667})
		item = frappe.db.get_value(
			"Charge Code", frappe.db.get_value("Rate Plan", self.plan.name, "room_charge_code"), "item"
		)
		whole = taxes.compute(CODE, item, 10000, inclusive=True, on_date=self.today)
		self.assertTrue(whole.tax_minor)
		self.assertEqual(sum(flt(line.tax_amount) for line in lines), whole.tax_minor / 100)
		for line in lines:
			# Per-account rows add up to the line's tax, so the invoice can carry them.
			rows = frappe.parse_json(line.tax_breakdown)
			self.assertAlmostEqual(sum(row["amount"] for row in rows), flt(line.tax_amount), places=2)

	def test_the_split_always_adds_up(self):
		a, b, c = "A", "B", "C"
		self.assertEqual(room_share.split(10001, [a, b], room_share.EQUAL, a, None, None), {a: 5001, b: 5000})
		self.assertEqual(
			room_share.split(10000, [a, b, c], room_share.EQUAL, b, None, None), {a: 3333, b: 3334, c: 3333}
		)
		shares = room_share.split(10000, [a, b, c], room_share.PERCENTAGE, a, 33.33, None)
		self.assertEqual((shares[a], sum(shares.values())), (3333, 10000))
		self.assertEqual(room_share.split(10000, [a, b], room_share.ENTIRE, a, None, b), {a: 0, b: 10000})

	def test_staggered_sharers_pay_their_own_rate_alone(self):
		"""Scenario 5: the sharer leaves first; the host pays the whole room after."""
		host = self.stay("Amani", nights=3)
		sharer = self.stay("Baraka", nights=1)
		room_share.join(sharer.name, host.name, room_share.EQUAL)
		self.assertEqual(
			self.rooms(host),
			{self.today: 5000, self.today + timedelta(days=1): 10000, self.today + timedelta(days=2): 10000},
		)
		self.assertEqual(self.rooms(sharer), {self.today: 5000})
		self.assertEqual([sold(self.today + timedelta(days=d)) for d in range(3)], [1, 1, 1])

		host = self.arrive(host, room="101")
		sharer = self.arrive(sharer)
		check_out(sharer.name, override_reason="Settles later")
		# The room stays occupied for the host.
		self.assertEqual(frappe.db.get_value("Hotel Room", f"{CODE}-101", "occupancy_status"), "Occupied")
		self.assertEqual(
			frappe.db.get_value(
				"Room Assignment", {"room_occupancy": host.room_occupancy, "status": "Occupied"}, "hotel_room"
			),
			f"{CODE}-101",
		)
		self.assertEqual(frappe.db.get_value("Stay Reservation", host.name, "status"), "In House")

	def test_a_sharer_arriving_first_widens_the_room(self):
		host = self.stay("Amani", arrival=self.today + timedelta(days=1), nights=2)
		sharer = self.stay("Baraka", arrival=self.today, nights=2)
		occupancy = room_share.join(sharer.name, host.name, room_share.OWN_RATE)
		span = frappe.db.get_value("Room Occupancy", occupancy, ["start_date", "end_date"])
		self.assertEqual(tuple(map(getdate, span)), (self.today, self.today + timedelta(days=3)))
		self.assertEqual([sold(self.today + timedelta(days=d)) for d in range(3)], [1, 1, 1])
		# Own Rate: each pays its booked rate, and the shared night records the split.
		self.assertEqual(self.rooms(sharer), {self.today: 10000, self.today + timedelta(days=1): 10000})
		shared_night = frappe.db.get_value(
			"Stay Rate Night",
			{"stay_reservation": host.name, "night_date": self.today + timedelta(days=1)},
			"share_distribution",
		)
		self.assertEqual(frappe.parse_json(shared_night)["levy_payer"], host.name)

	def test_cancelling_one_sharer_leaves_the_room_with_the_other(self):
		host, sharer = self.stay("Amani"), self.stay("Baraka")
		assign_room(host.name, f"{CODE}-102")
		occupancy = room_share.join(sharer.name, host.name, room_share.EQUAL)
		cancel(host.name, "Plans changed")

		self.assertEqual(frappe.db.get_value("Room Occupancy", occupancy, "allocation_state"), "Confirmed")
		self.assertEqual(frappe.db.get_value("Room Occupancy", occupancy, "share_mode"), "Single Account")
		self.assertEqual(sold(self.today), 1)
		self.assertEqual(self.rooms(sharer), {self.today: 10000, self.today + timedelta(days=1): 10000})
		# The room stays assigned, now in the sharer's name.
		self.assertEqual(
			frappe.db.get_value(
				"Room Assignment", {"room_occupancy": occupancy, "status": "Assigned"}, "stay_reservation"
			),
			sharer.name,
		)

	def test_separating_gives_the_sharer_its_own_room_and_rate(self):
		host, sharer = self.stay("Amani"), self.stay("Baraka")
		room_share.join(sharer.name, host.name, room_share.ENTIRE, payer=host.name)
		self.assertEqual(self.rooms(sharer), {self.today: 0, self.today + timedelta(days=1): 0})
		self.assertEqual(self.rooms(host), {self.today: 10000, self.today + timedelta(days=1): 10000})

		with self.assertRaises(room_share.ShareError):
			room_share.separate(sharer.name, "")
		new = room_share.separate(sharer.name, "Wants a quieter room")
		self.assertEqual(frappe.db.get_value("Stay Reservation", sharer.name, "room_occupancy"), new)
		self.assertEqual(sold(self.today), 2)
		self.assertEqual(self.rooms(sharer), {self.today: 10000, self.today + timedelta(days=1): 10000})
		self.assertFalse(room_share.is_shared(host.room_occupancy))

	def test_capacity_dates_and_roles_are_checked(self):
		host = self.stay("Amani", adults=2)
		too_many = self.stay("Baraka", adults=1)
		with self.assertRaises(room_share.ShareError):
			room_share.join(too_many.name, host.name)  # three adults in a room for two
		later = self.stay("Chausiku", arrival=self.today + timedelta(days=2))
		with self.assertRaises(room_share.ShareError):
			room_share.join(later.name, host.name)  # no night together

		single = self.stay("Dalila")
		other = self.stay("Eshe")
		frappe.set_user("Administrator")
		user = "room-share-agent@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Agent", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", user).add_roles("Reservations Agent")
		frappe.set_user(user)
		with self.assertRaises(frappe.PermissionError):
			room_share.join(other.name, single.name)  # different bookings need a manager
