"""F9 Taxes, packages, and occupancy pricing."""

from datetime import timedelta

import frappe
from frappe.utils import add_years, getdate

from frappoint.vuna_hospitality.services import allowances, quote
from frappoint.vuna_hospitality.services.folio import post_manual_charge, reverse_transaction
from frappoint.vuna_hospitality.services.money import to_minor
from frappoint.vuna_hospitality.services.reservations import confirm, hold
from frappoint.vuna_hospitality.services.stay_pricing import child_ages_on
from frappoint.vuna_hospitality.tests.test_folio import make_code, make_item, make_item_group
from frappoint.vuna_hospitality.tests.test_night_audit import NightAuditTestCase
from frappoint.vuna_hospitality.tests.test_reservations import stay_request

FOOD = "HSP Test Food"


def make_tax_template(company: str, name: str, rates: dict[str, float]) -> str:
	"""A Sales Taxes and Charges Template with one On Net Total row per (account name, rate)."""
	abbr = frappe.get_cached_value("Company", company, "abbr")
	parent = frappe.db.get_value(
		"Account", {"company": company, "is_group": 1, "root_type": "Liability"}, "name", order_by="lft desc"
	)
	rows = []
	for account_name, rate in rates.items():
		account = f"{account_name} - {abbr}"
		if not frappe.db.exists("Account", account):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": account_name,
					"company": company,
					"parent_account": parent,
					"account_type": "Tax",
					"tax_rate": rate,
				}
			).insert(ignore_permissions=True)
		rows.append(
			{
				"charge_type": "On Net Total",
				"account_head": account,
				"description": account_name,
				"rate": rate,
			}
		)
	title = f"{name} - {abbr}"
	if not frappe.db.exists("Sales Taxes and Charges Template", title):
		frappe.get_doc(
			{"doctype": "Sales Taxes and Charges Template", "title": name, "company": company, "taxes": rows}
		).insert(ignore_permissions=True)
	return title


class PricingTestCase(NightAuditTestCase):
	CODE = "PKG"

	def setUp(self):
		super().setUp()
		make_item_group(FOOD)
		for code, group in (
			("HSP-TEST-BB-BREAKFAST", FOOD),
			("HSP-TEST-FULL-BREAKFAST", FOOD),
			("HSP-TEST-EXTRA-ADULT", None),
			("HSP-TEST-CHILD", None),
			("HSP-TEST-BREAKAGE", None),
			("HSP-TEST-TOURISM-LEVY", None),
		):
			make_item(
				code, group or frappe.db.get_value("Item", "HSP-TEST-ROOM-NIGHT", "item_group"), rate=1000
			)
		make_code("TFNB", item_group=FOOD)
		make_code("TBKF", item="HSP-TEST-BB-BREAKFAST")
		make_code("TBKA", item_group=FOOD, transaction_type="Allowance")
		for code, item in (
			("TXAD", "HSP-TEST-EXTRA-ADULT"),
			("TCHD", "HSP-TEST-CHILD"),
			("TBRK", "HSP-TEST-BREAKAGE"),
			("TLVY", "HSP-TEST-TOURISM-LEVY"),
		):
			make_code(code, item=item)
		self.prop.reload()
		self.prop.breakage_charge_code = "TBRK"
		self.prop.prices_include_tax = 1
		self.prop.save()

	def set_rate(self, amount, nights=5):
		frappe.db.set_value(
			"Room Rate Day",
			{
				"rate_plan": self.plan.name,
				"rate_date": ["between", [self.today, self.today + timedelta(days=nights - 1)]],
			},
			"rate",
			amount,
		)

	def add_breakfast_package(self, **component):
		package = frappe.get_doc(
			{
				"doctype": "Hotel Package",
				"property": self.CODE,
				"package_name": "Bed and Breakfast",
				"package_code": "BB",
				"components": [
					{
						"component_name": "Breakfast",
						"charge_code": "TBKF",
						"amount_basis": "Per Adult",
						"amount": 1000,
						"included_in_rate": 1,
						"is_allowance": 1,
						"allowance_charge_code": "TBKA",
						"valid_days": 1,
						**component,
					}
				],
			}
		).insert()
		self.plan.reload()
		self.plan.package = package.name
		self.plan.tax_inclusive = 1
		self.plan.save()
		return package

	def lines(self, stay, prefix="night:"):
		return frappe.get_all(
			"Folio Transaction",
			filters={"stay_reservation": stay.name, "posting_key": ["like", f"{prefix}%"]},
			fields=["posting_key", "charge_code", "direction", "net_amount", "tax_amount", "gross_amount"],
			order_by="posting_key asc",
		)


class TestBreakfastPackage(PricingTestCase):
	def test_package_night_splits_and_breakfast_nets_to_zero(self):
		"""Scenario 20: nightly postings sum to the package price, a consumed breakfast nets to
		zero, and an unused one moves to breakage."""
		self.set_rate(12000)
		self.add_breakfast_package()
		stay = self.in_house_stay(nights=2)
		self.audit()

		night = {
			row.charge_code: row.gross_amount for row in self.lines(stay, f"night:{stay.name}:{self.today}")
		}
		self.assertEqual(night, {"TROOM": 10000, "TBKF": 2000})
		grants = allowances.open_grants(stay.name)
		self.assertEqual([to_minor(g.amount, "KES") for g in grants], [200000])

		# Adult 1 eats breakfast: the outlet charge is fully offset.
		charge = post_manual_charge(stay.default_folio, "HSP-TEST-FULL-BREAKFAST", rate=1000)
		self.assertEqual(len(charge["allowance_credits"]), 1)
		credit = frappe.get_doc("Folio Transaction", charge["allowance_credits"][0])
		self.assertEqual(
			(credit.charge_code, credit.direction, credit.gross_amount), ("TBKA", "Credit", 1000)
		)
		self.assertEqual(allowances.open_grants(stay.name)[0].remaining_minor, 100000)

		# The next audit closes the allowance's last day: the unused 1,000 moves to breakage.
		self.audit()
		expired = self.lines(stay, "exp:")
		self.assertEqual(
			sorted((row.charge_code, row.direction, row.gross_amount) for row in expired),
			[("TBKA", "Credit", 1000), ("TBRK", "Debit", 1000)],
		)
		balance = frappe.db.get_value("Guest Folio", stay.default_folio, "balance")
		self.assertEqual(balance, 24000)  # two package nights; breakfast and breakage net out

	def test_reversing_a_covered_charge_gives_the_allowance_back(self):
		self.set_rate(12000)
		self.add_breakfast_package()
		stay = self.in_house_stay(nights=2)
		self.audit()
		charge = post_manual_charge(stay.default_folio, "HSP-TEST-FULL-BREAKFAST", rate=1000)
		reverse_transaction(charge["name"], "Wrong guest")
		self.assertEqual(allowances.open_grants(stay.name)[0].remaining_minor, 200000)
		self.assertEqual(frappe.db.get_value("Guest Folio", stay.default_folio, "balance"), 12000)

	def test_check_out_expires_what_is_left(self):
		self.set_rate(12000)
		self.add_breakfast_package()
		stay = self.in_house_stay(nights=1)
		from frappoint.vuna_hospitality.services.front_desk import check_out

		check_out(stay.name, override_reason="Pays at the desk")
		self.assertEqual(allowances.open_grants(stay.name), [])

	def test_an_added_component_raises_the_price(self):
		self.set_rate(10000)
		self.add_breakfast_package(included_in_rate=0, is_allowance=0, allowance_charge_code=None)
		result = quote.quote(
			self.CODE, self.today, self.today + timedelta(days=1), f"{self.CODE}-STD", self.plan.name, 2
		)
		self.assertEqual(result.nights[0].amount_minor, to_minor(12000, "KES"))

	def test_package_setup_is_checked(self):
		with self.assertRaises(frappe.ValidationError):
			self.add_breakfast_package(charge_code="TFNB")  # covers a group, has no fixed Item
		with self.assertRaises(frappe.ValidationError):
			self.add_breakfast_package(amount_type="Percentage", amount=150)


class TestTaxes(PricingTestCase):
	def use_vat(self, inclusive=False):
		template = make_tax_template(
			self.prop.company, "HSP Test VAT", {"HSP Test VAT": 16, "HSP Test Levy": 2}
		)
		self.prop.reload()
		self.prop.sales_taxes_template = template
		self.prop.save()
		self.plan.reload()
		self.plan.tax_inclusive = int(inclusive)
		self.plan.save()

	def test_tax_inclusive_nights_add_up_exactly(self):
		"""Scenario 21: net plus taxes equals the inclusive rate on every night."""
		self.use_vat(inclusive=True)
		self.set_rate(12345.67)
		stay = self.in_house_stay(nights=3)
		for _day in range(3):
			self.audit()
		rooms = self.lines(stay)
		self.assertEqual(len(rooms), 3)
		for row in rooms:
			self.assertEqual(row.gross_amount, 12345.67)
			self.assertGreater(row.tax_amount, 0)
			self.assertEqual(
				to_minor(row.net_amount, "KES") + to_minor(row.tax_amount, "KES"), to_minor(12345.67, "KES")
			)

	def test_exclusive_rates_add_tax_on_top(self):
		self.use_vat()
		self.set_rate(10000)
		stay = self.in_house_stay(nights=1)
		self.audit()
		room = self.lines(stay)[0]
		self.assertEqual((room.net_amount, room.tax_amount, room.gross_amount), (10000, 1800, 11800))

	def test_quote_shows_the_tax(self):
		self.use_vat()
		self.set_rate(10000)
		args = (self.CODE, self.today, self.today + timedelta(days=2), f"{self.CODE}-STD", self.plan.name, 2)
		exclusive = quote.quote(*args)
		self.assertEqual((exclusive.total, exclusive.tax, exclusive.grand_total), (20000, 3600, 23600))
		self.plan.reload()
		self.plan.tax_inclusive = 1
		self.plan.save()
		inclusive = quote.quote(*args)
		self.assertEqual(inclusive.grand_total, inclusive.total)
		self.assertGreater(inclusive.tax, 0)

	def test_nightly_levy_posts_per_adult(self):
		self.prop.reload()
		self.prop.append("nightly_levies", {"charge_code": "TLVY", "basis": "Per Adult", "amount": 100})
		self.prop.save()
		stay = self.in_house_stay(nights=1)
		self.audit()
		levy = [row for row in self.lines(stay) if row.charge_code == "TLVY"]
		self.assertEqual([row.gross_amount for row in levy], [200])


class TestOccupancyPricing(PricingTestCase):
	def add_rule(self):
		return frappe.get_doc(
			{
				"doctype": "Occupancy Pricing Rule",
				"property": self.CODE,
				"rule_name": "Standard occupancy",
				"rate_plan": self.plan.name,
				"extra_adult_amount": 3000,
				"extra_adult_charge_code": "TXAD",
				"child_bands": [
					{"band_name": "Infant", "from_age": 0, "to_age": 2, "amount": 0},
					{
						"band_name": "Child",
						"from_age": 3,
						"to_age": 11,
						"amount": 1500,
						"charge_code": "TCHD",
					},
					{"band_name": "Teen", "from_age": 12, "to_age": 17, "price_as_adult": 1},
				],
			}
		).insert()

	def quote(self, adults, child_ages, nights=3):
		return quote.quote(
			self.CODE,
			self.today,
			self.today + timedelta(days=nights),
			f"{self.CODE}-STD",
			self.plan.name,
			adults,
			child_ages=child_ages,
		)

	def test_child_who_turns_12_mid_stay_keeps_the_arrival_band(self):
		"""Scenario 13: the age on the arrival date prices the whole stay."""
		self.set_rate(10000)
		self.add_rule()
		birthday = add_years(self.today + timedelta(days=1), -12)  # turns 12 on the second night
		ages = child_ages_on(self.today, [birthday])
		self.assertEqual(ages, [11])
		result = self.quote(1, ages)
		for night in result.nights:
			child = [c for c in night.components if c["key"] == "child:Child"]
			self.assertEqual([c["amount_minor"] for c in child], [150000])
		self.assertEqual(result.total_minor, to_minor(3 * 11500, "KES"))

		summary = hold(
			self.CODE,
			[stay_request(self.CODE, self.plan, self.guest, self.today, 3, adults=1, child_ages=ages)],
			booking_details={"booking_source": "Phone Calls"},
		)
		confirm(summary["stays"][0]["name"])
		stay = frappe.get_doc("Stay Reservation", summary["stays"][0]["name"])
		self.assertEqual((stay.children, frappe.parse_json(stay.child_ages)), (1, [11]))

	def test_teen_priced_as_adult_and_extra_adults_charged(self):
		self.set_rate(10000)
		self.add_rule()
		# 2 adults are the base; a 12-year-old counts as a third adult.
		components = self.quote(2, [12], nights=1).nights[0].components
		self.assertEqual(
			[(c["key"], c["amount_minor"]) for c in components],
			[("room", 1000000), ("extra-adult", 300000)],
		)
		self.assertEqual([c["key"] for c in self.quote(1, [1], nights=1).nights[0].components], ["room"])

	def test_night_audit_posts_each_extra_under_its_code(self):
		self.set_rate(10000)
		self.add_rule()
		summary = hold(
			self.CODE,
			[stay_request(self.CODE, self.plan, self.guest, self.today, 1, adults=1, child_ages=[5])],
			booking_details={"booking_source": "Phone Calls"},
		)
		confirm(summary["stays"][0]["name"])
		stay = frappe.get_doc("Stay Reservation", summary["stays"][0]["name"])
		from frappoint.vuna_hospitality.services.front_desk import assign_room, check_in, register_guest

		assign_room(stay.name, f"{self.CODE}-101")
		for guest in frappe.get_all("Stay Guest", filters={"stay_reservation": stay.name}, pluck="name"):
			register_guest(guest)
		check_in(stay.name)
		self.audit()
		self.assertEqual(
			sorted((row.charge_code, row.gross_amount) for row in self.lines(stay)),
			[("TCHD", 1500), ("TROOM", 10000)],
		)

	def test_overlapping_bands_are_refused(self):
		rule = frappe.get_doc(
			{
				"doctype": "Occupancy Pricing Rule",
				"property": self.CODE,
				"rule_name": "Bad",
				"rate_plan": self.plan.name,
				"child_bands": [
					{"band_name": "A", "from_age": 0, "to_age": 5, "amount": 0},
					{"band_name": "B", "from_age": 5, "to_age": 11, "amount": 0},
				],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			rule.insert()

	def test_unknown_ages_use_the_oldest_child_band(self):
		self.set_rate(10000)
		self.add_rule()
		components = self.quote(1, [None], nights=1).nights[0].components
		self.assertIn(("child:Child", 150000), [(c["key"], c["amount_minor"]) for c in components])
		self.assertEqual(getdate(self.today), self.today)
