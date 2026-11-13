"""F11 Multiple folios, settlement, and AR."""

from datetime import timedelta
from unittest.mock import patch

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

from frappoint.vuna_hospitality.api import folios as folios_api
from frappoint.vuna_hospitality.services import cashiering, folio, settlement
from frappoint.vuna_hospitality.services.front_desk import check_out
from frappoint.vuna_hospitality.services.money import to_minor
from frappoint.vuna_hospitality.services.reservations import _grant_settlement_access
from frappoint.vuna_hospitality.services.settlement import CreditLimitError, SettlementError
from frappoint.vuna_hospitality.tests.test_cashiering import CashierTestCase
from frappoint.vuna_hospitality.tests.test_folio import make_user
from frappoint.vuna_hospitality.tests.test_pricing_packages import make_tax_template
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled

FACIAL = "HSP-TEST-HYDRA-FACIAL"


def make_company_customer(name: str, credit_limit: float = 0, company: str | None = None) -> str:
	if not frappe.db.exists("Customer", name):
		doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_type": "Company",
				"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
				"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name"),
			}
		)
		if credit_limit:
			doc.append("credit_limits", {"company": company, "credit_limit": credit_limit})
		doc.insert(ignore_permissions=True)
	return name


class SettlementTestCase(CashierTestCase):
	CODE = "STL"

	def setUp(self):
		super().setUp()
		_grant_settlement_access()
		template = make_tax_template(
			self.prop.company, "HSP Test VAT", {"HSP Test VAT": 16, "HSP Test Levy": 2}
		)
		frappe.db.set_value(
			"Hotel Property", self.CODE, {"sales_taxes_template": template, "prices_include_tax": 1}
		)
		cashiering.open_shift(self.CODE)
		self.currency = self.prop.currency

	def facial(self, folio_name=None, rate=1001):
		"""A taxed charge with an odd amount, so splitting it has rounding to conserve."""
		return folio.post_manual_charge(folio_name or self.folio, FACIAL, rate=rate)["name"]

	def check_out(self):
		frappe.db.set_value("Hotel Property", self.CODE, "business_date", self.today + timedelta(days=1))
		check_out(self.stay.name, override_reason="Settles at the desk")

	def balance(self, folio_name=None):
		return frappe.db.get_value("Guest Folio", folio_name or self.folio, "balance")

	def line(self, name):
		return frappe.db.get_value(
			"Folio Transaction",
			name,
			[
				"guest_folio",
				"direction",
				"gross_amount",
				"tax_amount",
				"tax_breakdown",
				"transfer_of",
				"transfer_folio",
			],
			as_dict=True,
		)

	def settle_paid(self, folio_name=None):
		folio_name = folio_name or self.folio
		self.pay(self.balance(folio_name), folio_name=folio_name)
		return settlement.settle(folio_name)


class TestFolios(SettlementTestCase):
	def test_a_stay_opens_more_folios_up_to_the_limit(self):
		company = make_company_customer("HSP Test Acme Ltd")
		extra = settlement.add_folio(self.stay.name, "Company", payee_customer=company)
		row = frappe.db.get_value(
			"Guest Folio", extra, ["payee_customer", "payee_name", "window_number"], as_dict=True
		)
		self.assertEqual((row.payee_customer, row.payee_name, row.window_number), (company, company, 2))

		frappe.db.set_value("Hotel Property", self.CODE, "max_folios_per_stay", 2)
		with self.assertRaises(SettlementError):
			settlement.add_folio(self.stay.name, "Spouse")

	def test_the_payee_changes_only_until_a_payment(self):
		company = make_company_customer("HSP Test Acme Ltd")
		settlement.set_payee(self.folio, payee_customer=company)
		self.assertEqual(frappe.db.get_value("Guest Folio", self.folio, "payee_customer"), company)
		self.pay(100)
		with self.assertRaises(SettlementError):
			settlement.set_payee(self.folio, payee_guest_profile=self.guest.name)


class TestTransfers(SettlementTestCase):
	def test_half_a_charge_moves_and_every_minor_unit_is_kept(self):
		"""Scenario 22: amounts conserve exactly, with lineage on both folios."""
		charge = self.facial()
		original = self.line(charge)
		other = settlement.add_folio(self.stay.name, "Spouse")

		half = settlement.transfer(charge, other, 500.5, reason="Spouse pays half")
		moved_out, moved_in = self.line(half["out"]), self.line(half["in"])
		self.assertEqual((moved_out.guest_folio, moved_out.direction), (self.folio, "Credit"))
		self.assertEqual((moved_in.guest_folio, moved_in.direction), (other, "Debit"))
		for leg in (moved_out, moved_in):
			self.assertEqual(leg.transfer_of, charge)
			self.assertEqual(leg.gross_amount, 500.5)
		self.assertEqual((moved_out.transfer_folio, moved_in.transfer_folio), (other, self.folio))
		self.assertEqual(moved_out.tax_amount, moved_in.tax_amount)

		rest = settlement.transfer(charge, other)  # whatever is left
		parts = [self.line(rest["in"]), moved_in]
		for field in ("gross_amount", "tax_amount"):
			self.assertEqual(
				sum(to_minor(row[field], self.currency) for row in parts),
				to_minor(original[field], self.currency),
			)
		for account in {row["account"] for row in frappe.parse_json(original.tax_breakdown)}:
			split = sum(
				to_minor(entry["amount"], self.currency)
				for row in parts
				for entry in frappe.parse_json(row.tax_breakdown)
				if entry["account"] == account
			)
			whole = next(
				e["amount"] for e in frappe.parse_json(original.tax_breakdown) if e["account"] == account
			)
			self.assertEqual(split, to_minor(whole, self.currency))
		self.assertEqual(self.balance(other), 1001)
		with self.assertRaises(SettlementError):
			settlement.transfer(charge, other, 1)  # nothing left to move

	def test_a_retried_transfer_moves_once(self):
		charge = self.facial()
		other = settlement.add_folio(self.stay.name, "Spouse")
		first = settlement.transfer(charge, other, 200, request_id="move-1")
		self.assertEqual(settlement.transfer(charge, other, 200, request_id="move-1"), first)
		self.assertEqual(self.balance(other), 200)

	def test_moved_charges_are_reversed_on_their_own_folio(self):
		charge = self.facial()
		other = settlement.add_folio(self.stay.name, "Spouse")
		moved = settlement.transfer(charge, other, 400)
		with self.assertRaises(folio.PostingError):
			folio.reverse_transaction(charge, "Wrong guest")  # part of it lives elsewhere
		with self.assertRaises(folio.PostingError):
			folio.reverse_transaction(moved["out"], "Undo")
		folio.reverse_transaction(moved["in"], "Not the spouse's")
		self.assertEqual(self.balance(other), 0)

		reversed_charge = self.facial()
		folio.reverse_transaction(reversed_charge, "Posted twice")
		with self.assertRaises(SettlementError):
			settlement.transfer(reversed_charge, other)

	def test_charges_move_only_within_the_stay_or_booking(self):
		charge = self.facial()
		elsewhere = self.in_house_stay_elsewhere()
		with self.assertRaises(SettlementError):
			settlement.transfer(charge, elsewhere)

	def in_house_stay_elsewhere(self):
		stay = self.confirmed_stay(nights=1)
		return stay.default_folio


class TestSettlement(SettlementTestCase):
	def test_a_paid_folio_becomes_one_invoice_and_closes(self):
		self.facial()
		self.check_out()
		total = self.balance()
		result = self.settle_paid()
		self.assertEqual(result["status"], "Closed")

		invoice = frappe.get_doc("Sales Invoice", result["sales_invoice"])
		self.assertEqual(invoice.docstatus, 1)
		self.assertEqual(invoice.custom_guest_folio, self.folio)
		self.assertEqual(invoice.customer, frappe.db.get_value("Guest Folio", self.folio, "payee_customer"))
		self.assertEqual(to_minor(invoice.grand_total, self.currency), to_minor(total, self.currency))
		self.assertEqual(invoice.outstanding_amount, 0)  # the payment is the invoice's advance
		self.assertEqual(sum(row.allocated_amount for row in invoice.advances), total)
		self.assertGreater(invoice.total_taxes_and_charges, 0)
		unbilled = frappe.get_all(
			"Folio Transaction",
			filters={
				"guest_folio": self.folio,
				"transaction_type": "Revenue",
				"sales_invoice": ["is", "not set"],
			},
		)
		self.assertEqual(unbilled, [])

		# Settling again returns the same invoice.
		self.assertEqual(settlement.settle(self.folio)["sales_invoice"], invoice.name)
		with self.assertRaises(folio.FolioClosedError):
			self.facial()

	def test_lines_are_grouped_by_print_group(self):
		frappe.db.set_value("Charge Code", "TMSG", "print_group", "Spa and Wellness")
		frappe.db.set_value("Charge Code", "TSPA", "print_group", "Spa and Wellness")
		self.facial()
		self.check_out()
		invoice = frappe.get_doc("Sales Invoice", self.settle_paid()["sales_invoice"])
		names = {row.item_name for row in invoice.items}
		self.assertIn("Spa and Wellness", names)
		self.assertNotIn(frappe.db.get_value("Item", FACIAL, "item_name"), names)

	def test_a_folio_that_still_owes_is_not_settled(self):
		self.check_out()
		with self.assertRaises(SettlementError):
			settlement.settle(self.folio)

	def test_nights_not_charged_yet_block_settlement(self):
		self.pay(self.balance())
		with self.assertRaises(SettlementError):
			settlement.settle(self.folio)

	def test_the_booking_sales_partner_earns_commission(self):
		if not frappe.db.exists("Sales Partner", "HSP Test Agent"):
			frappe.get_doc(
				{
					"doctype": "Sales Partner",
					"partner_name": "HSP Test Agent",
					"commission_rate": 10,
					"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name"),
				}
			).insert(ignore_permissions=True)
		frappe.db.set_value("Hotel Booking", self.stay.hotel_booking, "sales_partner", "HSP Test Agent")
		self.check_out()
		invoice = frappe.get_doc("Sales Invoice", self.settle_paid()["sales_invoice"])
		self.assertEqual((invoice.sales_partner, invoice.commission_rate), ("HSP Test Agent", 10))

	def test_a_rejected_submission_leaves_the_folio_pending_and_a_retry_invoices_once(self):
		"""Scenario 26: an installed app's hook rejects the invoice."""
		self.check_out()
		self.pay(self.balance())

		def reject(_invoice):
			frappe.throw("The tax authority is unreachable")

		with patch.object(SalesInvoice, "on_submit", reject):
			result = settlement.settle(self.folio)
		self.assertEqual(result["status"], "Settlement Pending")
		self.assertIn("unreachable", result["error"])
		self.assertIsNone(result["sales_invoice"])
		self.assertFalse(frappe.db.exists("Sales Invoice", {"custom_guest_folio": self.folio}))
		with self.assertRaises(folio.FolioClosedError):
			self.facial()

		retried = settlement.settle(self.folio)
		self.assertEqual(retried["status"], "Closed")
		self.assertIsNone(frappe.db.get_value("Guest Folio", self.folio, "settlement_error"))
		self.assertEqual(frappe.db.count("Sales Invoice", {"custom_guest_folio": self.folio}), 1)

	def test_a_pending_folio_can_be_reopened_to_correct_it(self):
		self.check_out()
		self.pay(self.balance())
		with patch.object(SalesInvoice, "on_submit", lambda _doc: frappe.throw("Rejected")):
			settlement.settle(self.folio)
		settlement.release_settlement(self.folio, "Fix the Item's tax code")
		self.assertEqual(frappe.db.get_value("Guest Folio", self.folio, "status"), "Open")


class TestCompanyBilling(SettlementTestCase):
	def company_folio(self, credit_limit=0):
		company = make_company_customer("HSP Test Acme Ltd", credit_limit, self.prop.company)
		return settlement.add_folio(self.stay.name, "Acme", payee_customer=company), company

	def test_corporate_guest_room_to_the_company_extras_to_the_guest(self):
		"""Scenario 4: the room goes to the company's account; the spa stays personal."""
		self.check_out()
		company_folio, company = self.company_folio()
		rooms = frappe.get_all(
			"Folio Transaction",
			filters={"guest_folio": self.folio, "posting_key": ["like", "night:%"]},
			pluck="name",
		)
		self.assertTrue(rooms)
		for room in rooms:
			settlement.transfer(room, company_folio, reason="Company pays the room")

		owed = self.balance(company_folio)
		result = settlement.settle(company_folio, transfer_to_ar=True)
		self.assertEqual(result["status"], "Transferred to AR")
		invoice = frappe.get_doc("Sales Invoice", result["sales_invoice"])
		self.assertEqual((invoice.customer, invoice.outstanding_amount), (company, owed))

		personal = self.settle_paid()
		personal_invoice = frappe.get_doc("Sales Invoice", personal["sales_invoice"])
		self.assertNotEqual(personal_invoice.customer, company)
		self.assertEqual(personal_invoice.outstanding_amount, 0)

	def test_an_individual_is_not_billed_on_account(self):
		self.check_out()
		with self.assertRaises(SettlementError):
			settlement.settle(self.folio, transfer_to_ar=True)

	def test_over_the_credit_limit_only_the_credit_controller_approves(self):
		"""Scenario 27."""
		company_folio, _company = self.company_folio(credit_limit=100)
		self.facial(company_folio)
		desk = make_user("frappoint-fdm@example.com", "Front Desk Manager")
		finance = make_user("frappoint-finance@example.com", "Front Desk Manager")
		frappe.get_doc("User", finance).add_roles("Accounts Manager")
		frappe.db.set_single_value("Accounts Settings", "credit_controller", "Accounts Manager")

		frappe.set_user(desk)
		with self.assertRaises(CreditLimitError):
			settlement.settle(company_folio, transfer_to_ar=True)
		frappe.set_user(finance)
		with self.assertRaises(CreditLimitError):
			settlement.settle(company_folio, transfer_to_ar=True)  # needs a reason
		result = settlement.settle(company_folio, transfer_to_ar=True, override_reason="Contract renewal")
		frappe.set_user("Administrator")
		self.assertEqual(result["status"], "Transferred to AR")
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log",
				{"reference_name": company_folio, "event_type": "Credit Limit Override"},
			)
		)


class TestCreditNotes(SettlementTestCase):
	def test_a_disputed_charge_gets_a_credit_note_and_the_invoice_is_untouched(self):
		"""Scenario 25."""
		charge = self.facial()
		self.check_out()
		invoice_name = self.settle_paid()["sales_invoice"]
		before = frappe.db.get_value("Sales Invoice", invoice_name, ["grand_total", "docstatus"])

		with self.assertRaises(folio.PostingError):
			folio.reverse_transaction(charge, "Disputed")
		result = settlement.credit_note(charge, "Guest says no facial was given")
		note = frappe.get_doc("Sales Invoice", result["credit_note"])
		self.assertEqual((note.is_return, note.docstatus, note.custom_guest_folio), (1, 1, self.folio))
		self.assertEqual(to_minor(note.grand_total, self.currency), -to_minor(1001, self.currency))
		reversal = frappe.db.get_value(
			"Folio Transaction", result["reversal"], ["reverses", "sales_invoice", "direction"], as_dict=True
		)
		self.assertEqual(
			(reversal.reverses, reversal.sales_invoice, reversal.direction), (charge, note.name, "Credit")
		)
		self.assertEqual(
			frappe.db.get_value("Sales Invoice", invoice_name, ["grand_total", "docstatus"]), before
		)

		self.assertEqual(settlement.credit_note(charge, "Again"), result)
		with self.assertRaises(SettlementError):
			settlement.credit_note(self.facial_on_open_folio(), "Not invoiced")

	def facial_on_open_folio(self):
		return self.facial(settlement.add_folio(self.stay.name, "Late"))


class TestSettlementApi(SettlementTestCase):
	def test_the_workspace_shows_the_invoice_preview_and_settles(self):
		self.facial()
		self.check_out()
		self.pay(self.balance())
		# A cashier settles without any rights on Sales Invoice.
		frappe.set_user(make_user("frappoint-settle-cashier@example.com", "Cashier"))
		with hospitality_enabled(True):
			details = folios_api.get_stay_folios(self.stay.name)
			entry = next(row for row in details["folios"] if row["folio"]["name"] == self.folio)
			self.assertEqual(entry["invoice"]["outstanding"], 0)
			self.assertTrue(entry["invoice"]["items"])
			result = folios_api.settle_folio(self.folio)
		self.assertEqual(result["settled"]["status"], "Closed")
