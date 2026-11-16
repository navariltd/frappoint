"""F13 Rate operations and restrictions."""

from datetime import timedelta

import frappe
from frappe.utils import add_days

from frappoint.vuna_hospitality.services import rates, reservations, restrictions
from frappoint.vuna_hospitality.services.front_desk import (
	StayChangeError,
	assign_room,
	change_departure,
	departure_change,
)
from frappoint.vuna_hospitality.services.inventory import InventoryUnavailableError
from frappoint.vuna_hospitality.services.night_audit import post_due_nights
from frappoint.vuna_hospitality.services.quote import quote, search
from frappoint.vuna_hospitality.services.reservations import HoldRefusedError
from frappoint.vuna_hospitality.tests.test_folio import FolioTestCase, make_user
from frappoint.vuna_hospitality.tests.test_reservations import counters, stay_request


class RateTestCase(FolioTestCase):
	CODE = "RTO"

	def setUp(self):
		super().setUp()
		self.room_type = f"{self.CODE}-STD"

	def derived_plan(self, code="DSC", parent=None, value=-10, rounding="Nearest", increment=50, **extra):
		doc = frappe.copy_doc(frappe.get_doc("Rate Plan", parent or self.plan.name))
		doc.update(
			{
				"rate_plan_code": code,
				"rate_plan_name": f"Derived {code}",
				"parent_rate_plan": parent or self.plan.name,
				"derivation_type": "Percentage",
				"derivation_value": value,
				"rounding_rule": rounding,
				"rounding_increment": increment,
				"last_derived_on": None,
				**extra,
			}
		)
		return doc.insert(ignore_permissions=True)

	def rate(self, plan, night):
		return frappe.db.get_value(
			"Room Rate Day",
			{"rate_plan": plan, "room_type": self.room_type, "rate_date": night},
			["rate", "source", "is_manual_override"],
			as_dict=True,
		)

	def next_weekday(self, weekday: int, after: int = 1):
		"""The first date from `after` days ahead that falls on `weekday` (0 = Monday)."""
		night = self.today + timedelta(days=after)
		while night.weekday() != weekday:
			night += timedelta(days=1)
		return night

	def sold(self, night) -> int:
		"""Rooms sold that night; no inventory row yet means none."""
		row = counters(self.CODE, night)
		return row[1] if row else 0

	def as_user(self, role):
		frappe.set_user(make_user(f"f13-{role.lower().replace(' ', '-')}@example.com", role))


class TestDerivedPlans(RateTestCase):
	"""Scenario 11."""

	def test_a_derived_plan_follows_its_parent_rounded_and_keeps_manual_overrides(self):
		night, other = self.today + timedelta(days=2), self.today + timedelta(days=3)
		rates.set_rates(self.plan.name, [self.room_type], [night, other], rate=10030)
		plan = self.derived_plan()

		# 10,030 less 10% is 9,027, rounded to the nearest 50.
		self.assertEqual(self.rate(plan.name, night).rate, 9050)
		self.assertEqual(self.rate(plan.name, night).source, "Derivation")

		# A hand edit on the derived plan is a manual override...
		doc = frappe.get_doc("Room Rate Day", rates.rate_day_name(plan.name, "STD", night))
		doc.rate = 8800
		doc.save()
		self.assertEqual(
			(self.rate(plan.name, night).rate, self.rate(plan.name, night).is_manual_override), (8800, 1)
		)

		# ...which survives the parent changing, while the other nights follow it.
		rates.set_rates(self.plan.name, [self.room_type], [night, other], rate=11000)
		self.assertEqual(self.rate(plan.name, night).rate, 8800)
		self.assertEqual(self.rate(plan.name, other).rate, 9900)

		# Resetting gives the night its derived rate again.
		rates.reset_to_derived(plan.name, [self.room_type], [night])
		self.assertEqual(
			(self.rate(plan.name, night).rate, self.rate(plan.name, night).is_manual_override), (9900, 0)
		)

	def test_rounding_up_down_and_fixed_amounts(self):
		parent = frappe._dict(derivation_type="Percentage", derivation_value=-10)
		self.assertEqual(
			rates.derive_rate(
				10030, frappe._dict({**parent, "rounding_rule": "Up", "rounding_increment": 50})
			),
			9050,
		)
		self.assertEqual(
			rates.derive_rate(
				10030, frappe._dict({**parent, "rounding_rule": "Down", "rounding_increment": 50})
			),
			9000,
		)
		self.assertEqual(rates.derive_rate(10030, frappe._dict({**parent, "rounding_rule": "None"})), 9027)
		fixed = frappe._dict(derivation_type="Fixed Amount", derivation_value=-500, rounding_rule="None")
		self.assertEqual(rates.derive_rate(10030, fixed), 9530)
		self.assertEqual(rates.derive_rate(300, fixed), 0)

	def test_a_chain_of_derived_plans_follows_the_base(self):
		night = self.today + timedelta(days=2)
		first = self.derived_plan("DSC", value=-10, rounding="None")
		second = self.derived_plan("MBR", parent=first.name, value=-10, rounding="None")
		rates.set_rates(self.plan.name, [self.room_type], [night], rate=10000)
		self.assertEqual(self.rate(first.name, night).rate, 9000)
		self.assertEqual(self.rate(second.name, night).rate, 8100)

	def test_derivations_are_checked(self):
		plan = self.derived_plan()
		self.plan.reload()
		self.plan.parent_rate_plan = plan.name
		with self.assertRaises(frappe.ValidationError):
			self.plan.save()  # a loop
		season = frappe.get_doc(
			"Rate Season", frappe.db.get_value("Rate Season", {"rate_plan": self.plan.name})
		)
		season = frappe.copy_doc(season)
		season.rate_plan = plan.name
		with self.assertRaises(frappe.ValidationError):
			season.insert()  # a derived plan takes no season of its own
		with self.assertRaises(frappe.ValidationError):
			self.derived_plan("BAD", rounding="Nearest", increment=0)

	def test_the_grid_shows_derived_rates_and_overrides(self):
		from frappoint.vuna_hospitality.api import rates as rates_api
		from frappoint.vuna_hospitality.tests.utils import hospitality_enabled

		plan = self.derived_plan()
		night = self.today + timedelta(days=1)
		rates.set_rates(plan.name, [self.room_type], [night], rate=7000)
		with hospitality_enabled(True):
			grid = rates_api.get_rate_grid(self.CODE, plan.name, str(self.today), 7)
		cell = grid["rates"][self.room_type][str(night)]
		self.assertEqual((cell["rate"], cell["manual"]), (7000, True))
		self.assertTrue(grid["plan"]["is_derived"])
		self.assertIn("-10%", grid["plan"]["derivation"])


class TestRestrictions(RateTestCase):
	def restrict(self, night, rate_plan=None, room_type=None, **values):
		restrictions.set_restrictions(
			self.CODE,
			[night],
			rate_plans=[rate_plan],
			room_types=[room_type],
			values=values,
		)

	def quote_for(self, arrival, nights, **kwargs):
		return quote(
			self.CODE, arrival, arrival + timedelta(days=nights), self.room_type, self.plan.name, 2, **kwargs
		)

	def test_a_minimum_stay_rejects_a_short_quote_and_a_manager_overrides_it(self):
		"""Scenario 12."""
		friday = self.next_weekday(4)
		self.restrict(friday, min_stay_arrival=3)

		short = self.quote_for(friday, 2)
		self.assertFalse(short.offered)
		self.assertTrue(short.overridable)
		self.assertEqual(short.reasons, ["Minimum Stay 3 Nights"])
		self.assertTrue(self.quote_for(friday, 3).offered)

		request = stay_request(self.CODE, self.plan, self.guest, friday, 2)
		with self.assertRaises(HoldRefusedError):
			reservations.hold(self.CODE, [request], booking_details={"booking_source": "Phone Calls"})

		self.as_user("Reservations Agent")
		with self.assertRaises(frappe.PermissionError):
			reservations.hold(
				self.CODE,
				[{**request, "restriction_override_reason": "Regular guest"}],
				booking_details={"booking_source": "Phone Calls"},
			)
		self.as_user("Revenue Manager")
		summary = reservations.hold(
			self.CODE,
			[{**request, "restriction_override_reason": "Regular guest"}],
			booking_details={"booking_source": "Phone Calls"},
		)
		frappe.set_user("Administrator")
		stay = frappe.get_doc("Stay Reservation", summary["stays"][0]["name"])
		self.assertIn("Minimum Stay 3 Nights", stay.overridden_restrictions)
		self.assertEqual(stay.restriction_override_reason, "Regular guest")
		self.assertEqual(stay.restriction_override_by, "f13-revenue-manager@example.com")
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log",
				{
					"reference_name": stay.name,
					"event_type": "Restriction Overridden",
					"reason": "Regular guest",
				},
			)
		)

	def test_each_rule(self):
		arrival = self.today + timedelta(days=5)
		self.restrict(add_days(arrival, 1), closed=1)
		self.assertIn("Closed", self.quote_for(arrival, 3).reasons)
		self.assertTrue(self.quote_for(arrival, 1).offered)

		self.restrict(arrival, closed_to_arrival=1)
		self.assertIn("Closed to Arrival", self.quote_for(arrival, 1).reasons)

		later = self.today + timedelta(days=12)
		self.restrict(add_days(later, 2), closed_to_departure=1)
		self.assertIn("Closed to Departure", self.quote_for(later, 2).reasons)
		self.assertTrue(self.quote_for(later, 1).offered)

		self.restrict(later, max_stay=2)
		self.assertIn("Maximum Stay 2 Nights", self.quote_for(later, 4).reasons)

		through = self.today + timedelta(days=20)
		self.restrict(add_days(through, 1), min_stay_through=3)
		self.assertIn("Minimum Stay 3 Nights", self.quote_for(through, 2).reasons)

		ahead = self.today + timedelta(days=3)
		self.restrict(ahead, min_advance_days=7)
		self.assertIn("Book 7 Days Ahead", self.quote_for(ahead, 1).reasons)
		far = self.today + timedelta(days=25)
		self.restrict(far, max_advance_days=10)
		self.assertIn("Book Within 10 Days", self.quote_for(far, 1).reasons)

	def test_the_most_specific_row_wins(self):
		night = self.today + timedelta(days=4)
		self.restrict(night, closed=1)  # every plan and room type
		self.assertIn("Closed", self.quote_for(night, 1).reasons)
		# A row for this plan and room type, without "closed", wins over the property-wide row.
		self.restrict(night, rate_plan=self.plan.name, room_type=self.room_type, max_stay=5)
		self.assertTrue(self.quote_for(night, 1).offered)

	def test_clearing_and_empty_rows_are_removed(self):
		night = self.today + timedelta(days=6)
		self.restrict(night, closed=1, max_stay=4)
		name = restrictions.row_name(self.CODE, None, None, night)
		self.assertEqual(
			frappe.db.get_value("Rate Restriction Day", name, "restriction_summary"), "Closed · Max 4"
		)
		self.restrict(night, closed=0, max_stay=0)
		self.assertFalse(frappe.db.exists("Rate Restriction Day", name))
		self.restrict(night, closed=1)
		restrictions.set_restrictions(self.CODE, [night], clear=True)
		self.assertFalse(frappe.db.exists("Rate Restriction Day", name))

	def test_search_shows_restricted_options_as_overridable(self):
		friday = self.next_weekday(4)
		self.restrict(friday, min_stay_arrival=3)
		option = search(self.CODE, friday, friday + timedelta(days=2), 2)[0]
		self.assertEqual((option.offered, option.overridable), (False, True))


class TestStayChanges(RateTestCase):
	def test_an_in_house_stay_is_extended_under_lock(self):
		stay = self.in_house_stay(nights=2)
		old = stay.departure_date
		sold = self.sold(old)

		result = change_departure(stay.name, add_days(old, 1))

		stay.reload()
		self.assertEqual((stay.departure_date, stay.nights, result["nights"]), (add_days(old, 1), 3, 1))
		self.assertEqual(self.sold(old), sold + 1)
		night = frappe.get_all(
			"Stay Rate Night",
			filters={"stay_reservation": stay.name, "night_date": old},
			fields=["posting_state", "total"],
		)[0]
		self.assertEqual(night.posting_state, "Pending")
		self.assertEqual(
			stay.total_amount,
			sum(frappe.get_all("Stay Rate Night", filters={"stay_reservation": stay.name}, pluck="total")),
		)
		assignment = frappe.db.get_value(
			"Room Assignment", {"stay_reservation": stay.name, "status": "Occupied"}, "end_date"
		)
		self.assertEqual(assignment, add_days(old, 1))

	def test_an_extension_into_a_taken_room_or_a_full_night_is_refused(self):
		stay = self.in_house_stay(nights=2)
		old = stay.departure_date
		# Another guest arrives in the same room the day the stay was due to leave.
		follower = self.confirmed_stay(nights=1, arrival=old)
		assign_room(follower.name, f"{self.CODE}-101")
		with self.assertRaises(StayChangeError):
			change_departure(stay.name, add_days(old, 1))

		# With the room free, a sold-out night refuses the extension.
		reservations.cancel(follower.name, "Changed plans")
		for _ in range(2):
			self.confirmed_stay(nights=1, arrival=old)
		with self.assertRaises((StayChangeError, InventoryUnavailableError)):
			change_departure(stay.name, add_days(old, 1))
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "departure_date"), old)

	def test_an_extension_against_a_restriction_needs_an_override(self):
		stay = self.in_house_stay(nights=2)
		new_departure = add_days(stay.departure_date, 1)
		restrictions.set_restrictions(self.CODE, [new_departure], values={"closed_to_departure": 1})
		self.assertTrue(departure_change(stay.name, new_departure).restrictions)
		with self.assertRaises(restrictions.RestrictionError):
			change_departure(stay.name, new_departure)
		change_departure(stay.name, new_departure, override_reason="Late flight")
		stay.reload()
		self.assertEqual(stay.departure_date, new_departure)
		self.assertIn("Closed to Departure", stay.overridden_restrictions)

	def test_a_confirmed_stay_is_shortened_and_extended_again(self):
		arrival = self.today + timedelta(days=3)
		stay = self.confirmed_stay(nights=3, arrival=arrival)
		last = add_days(arrival, 2)
		sold = self.sold(last)

		change_departure(stay.name, last)
		stay.reload()
		self.assertEqual((stay.departure_date, stay.nights), (last, 2))
		self.assertEqual(self.sold(last), sold - 1)
		state = frappe.db.get_value(
			"Stay Rate Night", {"stay_reservation": stay.name, "night_date": last}, "posting_state"
		)
		self.assertEqual(state, "Cancelled")

		# The night comes back, priced again, on the same row.
		change_departure(stay.name, add_days(last, 1))
		state = frappe.db.get_value(
			"Stay Rate Night", {"stay_reservation": stay.name, "night_date": last}, "posting_state"
		)
		self.assertEqual(state, "Pending")
		self.assertEqual(self.sold(last), sold)

	def test_a_charged_night_cannot_be_dropped(self):
		stay = self.in_house_stay(nights=3)
		post_due_nights(stay.name, add_days(self.today, 1), self.today)
		with self.assertRaises(StayChangeError):
			change_departure(stay.name, self.today)

	def test_extending_a_due_out_stay_makes_it_in_house_again(self):
		stay = self.in_house_stay(nights=1)
		frappe.db.set_value("Stay Reservation", stay.name, "status", "Due Out")
		change_departure(stay.name, add_days(stay.departure_date, 2))
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "status"), "In House")
