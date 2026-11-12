"""F10 Payments and cashier shifts."""

from datetime import timedelta
from unittest.mock import patch

import frappe

from frappoint.vuna_hospitality.api import cashiering as cashiering_api
from frappoint.vuna_hospitality.services import cashiering, folio
from frappoint.vuna_hospitality.services.cashiering import CashieringError, NoOpenShiftError
from frappoint.vuna_hospitality.services.front_desk import check_out
from frappoint.vuna_hospitality.services.reservations import _grant_account_select_access
from frappoint.vuna_hospitality.tests.test_folio import FolioTestCase, make_user
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled

CASH, CARD, MPESA = "HSP Test Cash", "HSP Test Card", "HSP Test M-Pesa"


def leaf_account(company: str, **filters) -> str | None:
	return frappe.db.get_value("Account", {"company": company, "is_group": 0, **filters}, "name")


def make_mode(name: str, mode_type: str, company: str, account: str) -> str:
	if not frappe.db.exists("Mode of Payment", name):
		frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": name,
				"type": mode_type,
				"enabled": 1,
				"accounts": [{"company": company, "default_account": account}],
			}
		).insert(ignore_permissions=True)
	return name


def make_payment_code(code: str, mode: str) -> None:
	if not frappe.db.exists("Charge Code", code):
		frappe.get_doc(
			{
				"doctype": "Charge Code",
				"code": code,
				"description": f"Test {mode}",
				"transaction_type": "Payment",
				"mode_of_payment": mode,
			}
		).insert(ignore_permissions=True)


class CashierTestCase(FolioTestCase):
	CODE = "CSH"

	def setUp(self):
		super().setUp()
		# Installed after migrate; a fresh test site may not have run it yet.
		_grant_account_select_access()
		company = self.prop.company
		cash = leaf_account(company, account_type="Cash")
		bank = leaf_account(company, account_type="Bank") or cash
		for mode, mode_type, account, code in (
			(CASH, "Cash", cash, "TCASH"),
			(CARD, "Bank", bank, "TCARD"),
			(MPESA, "Phone", bank, "TMPESA"),
		):
			make_mode(mode, mode_type, company, account)
			make_payment_code(code, mode)
		if not frappe.db.exists("Payment Gateway", "Mpesa-Test"):
			frappe.get_doc({"doctype": "Payment Gateway", "gateway": "Mpesa-Test"}).insert(
				ignore_permissions=True
			)
		self.prop.reload()
		self.prop.cash_over_short_account = leaf_account(company, root_type="Expense")
		self.prop.save()
		self.stay = self.in_house_stay(nights=2)
		self.folio = self.stay.default_folio
		self.massage(self.folio)  # 4,500 owing

	def pay(self, amount, mode=CASH, folio_name=None, **kwargs):
		return cashiering.take_payment(
			self.CODE, [{"folio": folio_name or self.folio, "amount": amount}], mode_of_payment=mode, **kwargs
		)

	def phone_payment(self, splits):
		"""A pending M-Pesa payment, with the STK push stubbed out."""
		with (
			patch.object(cashiering, "_request_phone_payment"),
			patch.object(cashiering, "gateway_mode_of_payment", return_value=MPESA),
		):
			return cashiering.take_payment(
				self.CODE, splits, payment_gateway="Mpesa-Test", phone="0712345678"
			)

	def callback(self, payment):
		frappe.get_doc("Folio Payment", payment).run_method("on_payment_authorized", "Completed")

	def balance(self, folio_name=None):
		return frappe.db.get_value("Guest Folio", folio_name or self.folio, "balance")


class TestTakingPayments(CashierTestCase):
	def test_payments_need_an_open_shift(self):
		with self.assertRaises(NoOpenShiftError):
			self.pay(4500)

	def test_cash_payment_creates_an_advance_and_a_folio_credit(self):
		cashiering.open_shift(self.CODE, opening_float=1000)
		payment = frappe.get_doc("Folio Payment", self.pay(4500))
		self.assertEqual(payment.status, "Received")

		entry = frappe.get_doc("Payment Entry", payment.payment_entry)
		self.assertEqual((entry.docstatus, entry.payment_type, entry.paid_amount), (1, "Receive", 4500))
		self.assertEqual(entry.unallocated_amount, 4500)  # an advance until settlement (F11)
		self.assertEqual(entry.party, frappe.db.get_value("Guest Folio", self.folio, "payee_customer"))

		allocation = frappe.get_doc("Folio Payment Allocation", payment.splits[0].allocation)
		self.assertEqual(allocation.posting_key, f"pay:{entry.name}:{self.folio}")
		credit = frappe.get_doc("Folio Transaction", allocation.folio_transaction)
		self.assertEqual(
			(credit.direction, credit.charge_code, credit.gross_amount), ("Credit", "TCASH", 4500)
		)
		self.assertEqual(self.balance(), 0)

	def test_the_same_request_takes_one_payment(self):
		cashiering.open_shift(self.CODE)
		first = self.pay(2000, request_id="desk-1")
		self.assertEqual(self.pay(2000, request_id="desk-1"), first)
		self.assertEqual(self.balance(), 2500)

	def test_a_settled_folio_lets_the_guest_check_out(self):
		cashiering.open_shift(self.CODE)
		first_night = frappe.db.get_value(
			"Stay Rate Night", {"stay_reservation": self.stay.name, "night_date": self.today}, "total"
		)
		# The massage, and the first night that check-out posts.
		self.pay(4500 + first_night)
		frappe.db.set_value("Hotel Property", self.CODE, "business_date", self.today + timedelta(days=1))
		check_out(self.stay.name)
		self.assertEqual(frappe.db.get_value("Stay Reservation", self.stay.name, "status"), "Checked Out")

	def test_payment_codes_and_amounts_are_checked(self):
		cashiering.open_shift(self.CODE)
		with self.assertRaises(CashieringError):
			self.pay(0)
		make_mode(
			"HSP Test Voucher",
			"General",
			self.prop.company,
			leaf_account(self.prop.company, account_type="Cash"),
		)
		with self.assertRaises(CashieringError):
			self.pay(100, mode="HSP Test Voucher")  # no Payment charge code uses it


class TestPhonePayments(CashierTestCase):
	def test_a_repeated_callback_receives_once(self):
		"""Scenario 32: the same callback, received repeatedly, makes one payment and one allocation."""
		cashiering.open_shift(self.CODE)
		payment = self.phone_payment([{"folio": self.folio, "amount": 4500}])
		self.assertEqual(frappe.db.get_value("Folio Payment", payment, "status"), "Pending")
		self.assertEqual(self.balance(), 4500)

		for _attempt in range(3):
			self.callback(payment)
		self.assertEqual(frappe.db.count("Payment Entry", {"remarks": ["like", f"%{payment}%"]}), 1)
		self.assertEqual(frappe.db.count("Folio Payment Allocation", {"folio_payment": payment}), 1)
		self.assertEqual(self.balance(), 0)

	def test_split_tender_across_two_folios(self):
		"""Scenario 33: one M-Pesa payment of 30,000 split 20,000 / 10,000 across two folios."""
		cashiering.open_shift(self.CODE)
		extras = folio.create_folio("Stay Reservation", self.stay.name, label="Extras").name
		folio.post(extras, "TROOM", 30000, posting_key="test:extras")
		payment = self.phone_payment(
			[{"folio": self.folio, "amount": 20000}, {"folio": extras, "amount": 10000}]
		)
		self.callback(payment)
		self.callback(payment)
		allocations = frappe.get_all(
			"Folio Payment Allocation", filters={"folio_payment": payment}, fields=["guest_folio", "amount"]
		)
		self.assertEqual(
			sorted((a.guest_folio, a.amount) for a in allocations),
			sorted([(self.folio, 20000), (extras, 10000)]),
		)
		entry = frappe.db.get_value("Folio Payment", payment, "payment_entry")
		self.assertEqual(frappe.db.get_value("Payment Entry", entry, "paid_amount"), 30000)
		self.assertEqual((self.balance(), self.balance(extras)), (4500 - 20000, 20000))

	def test_a_pending_payment_can_be_cancelled(self):
		cashiering.open_shift(self.CODE)
		payment = self.phone_payment([{"folio": self.folio, "amount": 4500}])
		cashiering.fail(payment, "Guest declined the prompt", status="Cancelled")
		with self.assertRaises(CashieringError):
			cashiering.receive(payment)
		self.assertEqual(self.balance(), 4500)


class TestRefunds(CashierTestCase):
	def test_part_of_a_payment_is_refunded_once(self):
		cashiering.open_shift(self.CODE)
		payment = self.pay(6000)  # 1,500 more than owed
		refund = frappe.get_doc(
			"Folio Payment", cashiering.refund(payment, {self.folio: 1500}, reason="Overpaid")
		)
		self.assertEqual(
			(refund.payment_type, refund.status, refund.refund_of), ("Refund", "Received", payment)
		)
		self.assertEqual(frappe.db.get_value("Payment Entry", refund.payment_entry, "payment_type"), "Pay")
		self.assertEqual(self.balance(), 0)
		self.assertEqual(cashiering.folio_payments(self.folio)[0]["refundable"], 4500)
		with self.assertRaises(CashieringError):
			cashiering.refund(payment, {self.folio: 5000}, reason="Too much")

	def test_a_refund_needs_a_reason(self):
		cashiering.open_shift(self.CODE)
		payment = self.pay(4500)
		with self.assertRaises(CashieringError):
			cashiering.refund(payment, {self.folio: 100}, reason=" ")


class TestShiftClose(CashierTestCase):
	def test_blind_close_with_a_variance_and_review(self):
		"""Scenario 35: counts are declared blind, a variance needs a reason and posts at review."""
		cashier = make_user("frappoint-cashier@example.com", "Cashier")
		supervisor = make_user("frappoint-supervisor@example.com", "Front Desk Manager")
		frappe.set_user(cashier)
		with hospitality_enabled(True):
			cashiering_api.open_shift(self.CODE, opening_float=1000)
			self.pay(4500)
			view = cashiering_api.get_cashier(self.CODE)
			self.assertEqual(view["shift"]["counts"], [])  # blind: nothing expected is shown
			shift = view["shift"]["name"]

			with self.assertRaises(CashieringError):
				cashiering.close_shift(shift, {CASH: 5300})
			closed = cashiering.close_shift(shift, {CASH: 5300}, {CASH: "A 200 note is missing"})
			count = closed["counts"][0]
			self.assertEqual((count["expected"], count["declared"], count["variance"]), (5500, 5300, -200))

			with self.assertRaises(frappe.PermissionError):
				cashiering.review_shift(shift)  # not by the cashier themselves

			frappe.set_user(supervisor)
			reviewed = cashiering_api.review_shift(shift, notes="Checked the safe")
			self.assertEqual(reviewed["to_review"], [])
		frappe.set_user("Administrator")
		journal = frappe.get_doc(
			"Journal Entry", frappe.db.get_value("Cashier Shift", shift, "journal_entry")
		)
		over_short = self.prop.cash_over_short_account
		self.assertEqual(
			sorted((row.account == over_short, row.debit, row.credit) for row in journal.accounts),
			[(False, 0, 200), (True, 200, 0)],
		)

	def test_a_shift_with_pending_phone_payments_cannot_close(self):
		shift = cashiering.open_shift(self.CODE)
		self.phone_payment([{"folio": self.folio, "amount": 4500}])
		with self.assertRaises(CashieringError):
			cashiering.close_shift(shift, {})

	def test_one_open_shift_per_cashier(self):
		cashiering.open_shift(self.CODE)
		with self.assertRaises(CashieringError):
			cashiering.open_shift(self.CODE)


class TestCashierApi(CashierTestCase):
	def test_cashiers_may_pick_accounts_but_not_read_them(self):
		rule = frappe.db.get_value(
			"Custom DocPerm", {"parent": "Account", "role": "Cashier", "permlevel": 0}, ["select", "read"]
		)
		self.assertEqual(rule, (1, 0))

	def test_night_auditors_cannot_take_payments(self):
		auditor = make_user("frappoint-audit-cash@example.com", "Night Auditor")
		frappe.set_user(auditor)
		with hospitality_enabled(True), self.assertRaises(frappe.PermissionError):
			cashiering_api.take_payment(
				self.CODE, [{"folio": self.folio, "amount": 100}], mode_of_payment=CASH
			)

	def test_folio_workspace_lists_payments(self):
		cashiering.open_shift(self.CODE)
		self.pay(4500)
		from frappoint.vuna_hospitality.api.folios import get_stay_folios

		with hospitality_enabled(True):
			details = get_stay_folios(self.stay.name)
		self.assertTrue(details["cashier_shift"])
		self.assertIn(CASH, details["payment_options"]["modes"])
		self.assertEqual(details["folios"][0]["payments"][0]["refundable"], 4500)
