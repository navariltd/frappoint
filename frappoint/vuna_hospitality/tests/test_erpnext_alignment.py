"""FA: hospitality uses ERPNext masters instead of its own copies."""

from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from frappoint.vuna_hospitality.doctype.charge_code import charge_code
from frappoint.vuna_hospitality.services import reservations
from frappoint.vuna_hospitality.services.guests import _default
from frappoint.vuna_hospitality.tests.test_reservations import make_booking_fixtures, stay_request


class TestChargeCodeUsesItemGroup(IntegrationTestCase):
	def setUp(self):
		frappe.db.savepoint("fa_test")
		make_booking_fixtures("FAC", rooms=1)

	def tearDown(self):
		frappe.db.rollback(save_point="fa_test")

	def test_item_group_comes_from_the_item(self):
		code = frappe.get_doc("Charge Code", "TROOM")
		self.assertEqual(code.item_group, frappe.db.get_value("Item", code.item, "item_group"))
		self.assertFalse(frappe.get_meta("Charge Code").has_field("charge_department"))
		self.assertFalse(frappe.db.exists("DocType", "Charge Department"))

	def test_tax_is_not_a_charge_code_type(self):
		code = frappe.get_doc("Charge Code", "TROOM")
		code.transaction_type = "Tax"
		with self.assertRaises(frappe.ValidationError):
			code.save()

	def test_revenue_item_needs_an_income_account_for_every_hotel_company(self):
		code = frappe.get_doc("Charge Code", "TROOM")
		with patch.object(charge_code, "income_account", return_value=None):
			with self.assertRaises(frappe.ValidationError):
				code.save()
		with patch.object(charge_code, "income_account", return_value="Sales - TC"):
			frappe.get_doc("Charge Code", "TROOM").save()


class TestBookingUsesUtmSourceAndSalesPartner(IntegrationTestCase):
	CODE = "FAB"

	def setUp(self):
		frappe.db.savepoint("fa_booking_test")
		self.prop, self.plan, self.guest = make_booking_fixtures(self.CODE, rooms=2)
		self.arrival = frappe.utils.getdate(self.prop.business_date) + timedelta(days=1)

	def tearDown(self):
		frappe.db.rollback(save_point="fa_booking_test")

	def hold(self, **details):
		return reservations.hold(
			self.CODE,
			[stay_request(self.CODE, self.plan, self.guest, self.arrival)],
			booking_details={"booking_source": "Phone Calls", **details},
		)

	def test_booking_source_is_a_utm_source(self):
		self.assertEqual(frappe.get_meta("Hotel Booking").get_field("booking_source").options, "UTM Source")
		self.assertFalse(frappe.db.exists("DocType", "Hotel Booking Source"))
		with self.assertRaises(frappe.LinkValidationError):
			self.hold(booking_source="No Such Source")

	def test_sales_partner_defaults_from_the_booker_customer(self):
		partner = frappe.get_doc(
			{
				"doctype": "Sales Partner",
				"partner_name": "FA Test Travel",
				"commission_rate": 10,
				"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name")
				or frappe.db.get_value("Territory", {}, "name"),
			}
		).insert(ignore_permissions=True)
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "FA Test Corporate",
				"customer_type": "Company",
				"customer_group": _default("customer_group", "Customer Group"),
				"territory": _default("territory", "Territory"),
				"default_sales_partner": partner.name,
			}
		).insert(ignore_permissions=True)

		summary = self.hold(booker_customer=customer.name)
		self.assertEqual(summary["sales_partner"], partner.name)
		explicit = self.hold(booker_customer=customer.name, sales_partner=None)
		self.assertEqual(explicit["sales_partner"], partner.name)

	def test_booking_desk_offers_the_settings_sources(self):
		settings = frappe.get_single("Hospitality Settings")
		settings.set("booking_sources", [{"utm_source": "Phone Calls"}])
		settings.save()
		self.assertEqual(reservations.booking_sources(), ["Phone Calls"])
		settings.set("booking_sources", [])
		settings.save()
		self.assertIn("Phone Calls", reservations.booking_sources())  # empty list: every UTM Source

	def test_hospitality_roles_can_pick_a_sales_partner(self):
		reservations._grant_sales_partner_access()
		roles = set(frappe.get_all("Custom DocPerm", filters={"parent": "Sales Partner"}, pluck="role"))
		self.assertIn("Reservations Agent", roles)
		self.assertIn("Sales User", roles)  # ERPNext's own rules are kept
