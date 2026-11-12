"""F3 Charge codes, rates, and quote."""

from datetime import date, timedelta

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from frappoint.vuna_hospitality.api.quote import search_availability
from frappoint.vuna_hospitality.services import inventory
from frappoint.vuna_hospitality.services.feature_flag import HospitalityDisabledError
from frappoint.vuna_hospitality.services.money import from_minor, to_minor
from frappoint.vuna_hospitality.services.quote import NO_RATE, SOLD_OUT, TOO_MANY_GUESTS, quote, search
from frappoint.vuna_hospitality.services.rates import generate_from_season, rate_day_name
from frappoint.vuna_hospitality.tests.utils import (
	hospitality_enabled,
	make_test_property,
	make_test_rate_setup,
	make_test_season,
)


def next_weekday(start: date, weekday: int) -> date:
	return start + timedelta(days=(weekday - start.weekday()) % 7)


class RatesTestCase(IntegrationTestCase):
	def setUp(self):
		frappe.db.savepoint("rates_test")
		self.prop, self.rooms = make_test_property(code="RTE", room_types={"STD": 2, "DLX": 1})
		self.plan = make_test_rate_setup("RTE")
		self.today = getdate(self.prop.business_date)
		# A Thursday at least a week ahead, so Thu-Sun spans a weekend.
		self.thursday = next_weekday(self.today + timedelta(days=7), 3)

	def tearDown(self):
		frappe.db.rollback(save_point="rates_test")

	def season(self, days=31, std=(10000, 12000), dlx=(15000, None)):
		return make_test_season(
			self.plan, self.today, self.today + timedelta(days=days - 1), {"RTE-STD": std, "RTE-DLX": dlx}
		)


class TestMoney(IntegrationTestCase):
	def test_minor_units_round_half_up(self):
		self.assertEqual(to_minor(12345.675, "KES"), 1234568)
		self.assertEqual(to_minor("0.1", "KES") + to_minor("0.2", "KES"), to_minor("0.3", "KES"))
		self.assertEqual(from_minor(1234568, "KES"), 12345.68)


class TestChargeCodesAndPlans(RatesTestCase):
	def test_rate_plan_name_carries_the_property(self):
		self.assertEqual(self.plan.name, "RTE-BAR")
		self.assertEqual(self.plan.currency, frappe.db.get_value("Hotel Property", "RTE", "currency"))

	def test_revenue_codes_need_an_item_and_payment_codes_a_mode_of_payment(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Charge Code",
					"code": "nitem",
					"description": "x",
					"transaction_type": "Revenue",
				}
			).insert()
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Charge Code",
					"code": "nmop",
					"description": "x",
					"transaction_type": "Payment",
				}
			).insert()

	def test_charge_code_is_upper_cased(self):
		code = frappe.get_doc(
			{
				"doctype": "Charge Code",
				"code": "rtecash",
				"description": "Cash",
				"transaction_type": "Payment",
				"mode_of_payment": frappe.db.get_value("Mode of Payment", {}, "name"),
			}
		).insert()
		self.assertEqual(code.name, "RTECASH")

	def test_rate_plan_policies_must_match_their_type(self):
		self.plan.cancellation_policy = self.plan.deposit_policy
		with self.assertRaises(frappe.ValidationError):
			self.plan.save()

	def test_policy_percentage_cannot_exceed_100(self):
		policy = frappe.get_doc(
			{
				"doctype": "Hotel Policy",
				"property": "RTE",
				"policy_name": "Too much",
				"policy_type": "Cancellation",
				"fee_type": "Percentage of Stay",
				"fee_value": 150,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			policy.insert()


class TestSeasonGeneration(RatesTestCase):
	def test_month_of_weekday_and_weekend_rates(self):
		result = generate_from_season(self.season().name)
		self.assertEqual(result["created"], 62)  # 31 nights x 2 room types

		friday = self.thursday + timedelta(days=1)
		rate = lambda rt, d: frappe.db.get_value("Room Rate Day", rate_day_name("RTE-BAR", rt, d), "rate")  # noqa: E731
		self.assertEqual(rate("STD", self.thursday), 10000)
		self.assertEqual(rate("STD", friday), 12000)  # Friday night uses the weekend rate
		self.assertEqual(rate("DLX", friday), 15000)  # no weekend rate given: weekday rate
		self.assertEqual(
			frappe.db.get_value("Room Rate Day", rate_day_name("RTE-BAR", "STD", friday), "source"), "Season"
		)
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log", {"reference_name": "RTE-BAR", "event_type": "Rates Generated"}
			)
		)

	def test_regenerating_is_idempotent(self):
		season = self.season(days=7)
		generate_from_season(season.name)
		again = generate_from_season(season.name)
		self.assertEqual((again["created"], again["updated"]), (0, 0))

	def test_manual_overrides_survive_unless_overwritten(self):
		season = self.season(days=7)
		generate_from_season(season.name)
		day = frappe.get_doc("Room Rate Day", rate_day_name("RTE-BAR", "STD", self.today))
		season_rate = day.rate  # weekday or weekend rate, depending on the business date
		day.rate = 8000
		day.save()
		self.assertEqual((day.source, day.is_manual_override), ("Manual", 1))

		self.assertEqual(generate_from_season(season.name)["skipped_manual"], 1)
		self.assertEqual(frappe.db.get_value("Room Rate Day", day.name, "rate"), 8000)

		generate_from_season(season.name, overwrite_manual=True)
		self.assertEqual(
			frappe.db.get_value("Room Rate Day", day.name, ["rate", "is_manual_override"]), (season_rate, 0)
		)

	def test_one_rate_per_plan_room_type_and_night(self):
		generate_from_season(self.season(days=1).name)
		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc(
				{
					"doctype": "Room Rate Day",
					"rate_plan": "RTE-BAR",
					"room_type": "RTE-STD",
					"rate_date": self.today,
					"rate": 1,
				}
			).insert()

	def test_season_room_types_must_belong_to_the_property(self):
		make_test_property(code="RTX", room_types={"STD": 1})
		with self.assertRaises(frappe.ValidationError):
			make_test_season(self.plan, self.today, self.today, {"RTX-STD": (100, None)})


class TestQuote(RatesTestCase):
	def setUp(self):
		super().setUp()
		generate_from_season(self.season().name)

	def test_three_nights_across_a_weekend(self):
		q = quote("RTE", self.thursday, self.thursday + timedelta(days=3), "RTE-STD", "RTE-BAR", adults=2)
		self.assertTrue(q.offered, q.reasons)
		self.assertEqual([n.rate for n in q.nights], [10000, 12000, 12000])  # Thu, Fri, Sat nights
		self.assertEqual(q.total_minor, 3400000)
		self.assertEqual(q.total, 34000)
		self.assertEqual(q.as_dict()["average_rate"], 11333.33)

	def test_quote_creates_and_locks_nothing(self):
		rows_before = frappe.db.count("Room Type Inventory Day", {"property": "RTE"})
		quote("RTE", self.thursday, self.thursday + timedelta(days=2), "RTE-STD", "RTE-BAR")
		self.assertEqual(frappe.db.count("Room Type Inventory Day", {"property": "RTE"}), rows_before)

	def test_sold_out_night_is_not_offered(self):
		inventory.acquire(
			"RTE-DLX", self.thursday + timedelta(days=1), self.thursday + timedelta(days=2), kind="sold"
		)
		q = quote("RTE", self.thursday, self.thursday + timedelta(days=3), "RTE-DLX", "RTE-BAR")
		self.assertFalse(q.offered)
		self.assertEqual(q.reasons, [SOLD_OUT])
		self.assertEqual([n.sellable for n in q.nights], [True, False, True])

	def test_night_without_a_rate_is_not_offered(self):
		after_season = self.today + timedelta(days=31)
		q = quote(
			"RTE", after_season - timedelta(days=1), after_season + timedelta(days=1), "RTE-STD", "RTE-BAR"
		)
		self.assertEqual(q.reasons, [NO_RATE])
		self.assertEqual(q.nights[-1].reason, NO_RATE)

	def test_too_many_guests(self):
		q = quote("RTE", self.thursday, self.thursday + timedelta(days=1), "RTE-STD", "RTE-BAR", adults=3)
		self.assertIn(TOO_MANY_GUESTS, q.reasons)

	def test_search_lists_offered_options_cheapest_first(self):
		inventory.acquire("RTE-DLX", self.thursday, self.thursday + timedelta(days=1), kind="sold")
		results = search("RTE", self.thursday, self.thursday + timedelta(days=1), adults=2)
		self.assertEqual([(q.room_type, q.offered) for q in results], [("RTE-STD", True), ("RTE-DLX", False)])

	def test_api_requires_hospitality_enabled(self):
		with hospitality_enabled(False), self.assertRaises(HospitalityDisabledError):
			search_availability("RTE", str(self.thursday), str(self.thursday + timedelta(days=1)))
		with hospitality_enabled(True):
			results = search_availability("RTE", str(self.thursday), str(self.thursday + timedelta(days=1)))
		self.assertEqual(results[0]["room_type"], "RTE-STD")
