"""Sales Partner commission billed to the partner's Supplier as a Purchase Invoice."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from frappoint.frappoint.services import partner_commission as commission
from frappoint.frappoint.services.partner_commission import CommissionPayoutError

COMPANY = "_Test Company"
SERVICE_ITEM = "PC-TEST-SERVICE"
COMMISSION_ITEM = "PC-TEST-COMMISSION"


def _default(doctype):
	return frappe.db.get_value(doctype, {"is_group": 0}, "name") or frappe.db.get_value(doctype, {}, "name")


def make_item(item_code, grant_commission=1):
	if not frappe.db.exists("Item", item_code):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": _default("Item Group"),
				"stock_uom": "Nos"
				if frappe.db.exists("UOM", "Nos")
				else frappe.db.get_value("UOM", {}, "name"),
				"is_stock_item": 0,
				"grant_commission": grant_commission,
			}
		).insert(ignore_permissions=True)


def make_partner(name, rate=10):
	return frappe.get_doc(
		{
			"doctype": "Sales Partner",
			"partner_name": name,
			"commission_rate": rate,
			"territory": _default("Territory"),
		}
	).insert(ignore_permissions=True)


class PartnerCommissionTestCase(IntegrationTestCase):
	def setUp(self):
		frappe.db.savepoint("partner_commission_test")
		if not frappe.db.exists("Company", COMPANY):
			self.skipTest(f"{COMPANY} is created by the test setup")
		make_item(SERVICE_ITEM)
		make_item(COMMISSION_ITEM, grant_commission=0)
		frappe.db.set_single_value("Selling Settings", "custom_commission_item", COMMISSION_ITEM)
		frappe.db.set_single_value("Selling Settings", "custom_commission_payable_on", "Submitted Invoices")
		self.customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "PC Test Customer",
				"customer_group": _default("Customer Group"),
				"territory": _default("Territory"),
			}
		).insert(ignore_permissions=True)
		self.partner = make_partner("PC Test Travel")

	def tearDown(self):
		frappe.db.rollback(save_point="partner_commission_test")

	def invoice(self, amount=1000, partner=None, return_against=None):
		"""A submitted Sales Invoice with the partner's commission (or a credit note against one)."""
		si = frappe.new_doc("Sales Invoice")
		si.update(
			{
				"customer": self.customer.name,
				"company": COMPANY,
				"posting_date": nowdate(),
				"due_date": nowdate(),
				"currency": frappe.get_cached_value("Company", COMPANY, "default_currency"),
				"sales_partner": (partner or self.partner).name,
				"commission_rate": (partner or self.partner).commission_rate,
				"is_return": int(bool(return_against)),
				"return_against": return_against,
			}
		)
		si.append("items", {"item_code": SERVICE_ITEM, "qty": -1 if return_against else 1, "rate": amount})
		si.set_missing_values()
		si.insert(ignore_permissions=True)
		si.submit()
		return si

	def payable(self, partner=None):
		return commission.get_payable_commissions(COMPANY, sales_partner=(partner or self.partner).name)


class TestPartnerSupplier(PartnerCommissionTestCase):
	def test_supplier_is_created_once_and_linked(self):
		supplier = commission.ensure_partner_supplier(self.partner.name)
		self.assertEqual(frappe.db.get_value("Supplier", supplier, "supplier_name"), "PC Test Travel")
		self.assertEqual(frappe.db.get_value("Sales Partner", self.partner.name, "custom_supplier"), supplier)
		self.assertEqual(commission.ensure_partner_supplier(self.partner.name), supplier)
		self.assertEqual(frappe.db.count("Supplier", {"supplier_name": "PC Test Travel"}), 1)

	def test_an_existing_supplier_with_the_same_name_is_linked(self):
		existing = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "PC Agency",
				"supplier_group": _default("Supplier Group"),
			}
		).insert(ignore_permissions=True)
		partner = make_partner("PC Agency")
		self.assertEqual(commission.ensure_partner_supplier(partner.name), existing.name)


class TestPayableCommission(PartnerCommissionTestCase):
	def test_commission_is_taken_from_the_invoice(self):
		si = self.invoice(amount=1000)
		rows = self.payable()
		self.assertEqual([(r.name, r.total_commission) for r in rows], [(si.name, si.total_commission)])
		self.assertEqual(si.total_commission, 100)

	def test_paid_invoices_setting_waits_for_payment(self):
		frappe.db.set_single_value("Selling Settings", "custom_commission_payable_on", "Paid Invoices")
		si = self.invoice()
		self.assertEqual(self.payable(), [])
		# The rule only looks at what is still owed on the invoice.
		frappe.db.set_value("Sales Invoice", si.name, "outstanding_amount", 0)
		self.assertEqual([r.name for r in self.payable()], [si.name])

	def test_credit_notes_reduce_the_payout(self):
		si = self.invoice(amount=1000)
		self.invoice(amount=400, return_against=si.name)
		self.assertEqual(sum(r.total_commission for r in self.payable()), 60)


class TestCommissionPurchaseInvoice(PartnerCommissionTestCase):
	def setUp(self):
		super().setUp()
		commission.ensure_partner_supplier(self.partner.name)

	def bill(self):
		return commission.make_commission_purchase_invoice(self.partner.name, COMPANY)

	def test_draft_purchase_invoice_bills_each_sales_invoice_once(self):
		first, second = self.invoice(amount=1000), self.invoice(amount=500)
		pi = frappe.get_doc("Purchase Invoice", self.bill())

		self.assertEqual(pi.docstatus, 0)
		self.assertEqual(pi.supplier, self.partner.reload().custom_supplier)
		self.assertEqual(sorted(row.rate for row in pi.items), [50, 100])
		self.assertEqual(pi.total, 150)
		self.assertTrue(all(row.item_code == COMMISSION_ITEM for row in pi.items))
		for si in (first, second):
			self.assertEqual(
				frappe.db.get_value("Sales Invoice", si.name, "custom_commission_purchase_invoice"), pi.name
			)

		self.assertEqual(self.payable(), [])
		with self.assertRaises(CommissionPayoutError):
			self.bill()

	def test_deleting_or_cancelling_the_purchase_invoice_frees_the_sales_invoices(self):
		si = self.invoice()
		frappe.delete_doc("Purchase Invoice", self.bill(), ignore_permissions=True)
		self.assertEqual([r.name for r in self.payable()], [si.name])

		pi = frappe.get_doc("Purchase Invoice", self.bill())
		pi.submit()
		pi.cancel()
		self.assertEqual([r.name for r in self.payable()], [si.name])

	def test_nothing_to_bill_after_credit_notes_is_refused(self):
		si = self.invoice(amount=500)
		self.invoice(amount=500, return_against=si.name)
		with self.assertRaises(CommissionPayoutError):
			self.bill()

	def test_partner_without_a_supplier_or_missing_item_is_refused(self):
		unlinked = make_partner("PC Unlinked Partner")
		self.invoice(partner=unlinked)
		with self.assertRaises(CommissionPayoutError):
			commission.make_commission_purchase_invoice(unlinked.name, COMPANY)

		frappe.db.set_single_value("Selling Settings", "custom_commission_item", None)
		self.invoice()
		with self.assertRaises(CommissionPayoutError):
			self.bill()

	def test_bulk_billing_reports_partners_it_could_not_bill(self):
		unlinked = make_partner("PC Unlinked Partner")
		self.invoice()
		self.invoice(partner=unlinked)
		result = commission.make_all_commission_purchase_invoices(COMPANY)
		self.assertEqual([row["sales_partner"] for row in result["created"]], [self.partner.name])
		self.assertEqual([row["sales_partner"] for row in result["skipped"]], [unlinked.name])

	def test_a_disabled_default_price_list_gives_a_clear_error(self):
		self.invoice()
		frappe.db.set_single_value("Buying Settings", "buying_price_list", "Standard Buying")
		with patch.object(commission, "_buying_price_list", return_value=None):
			with self.assertRaisesRegex(CommissionPayoutError, "buying Price List"):
				self.bill()


class TestBillSelectedInvoices(PartnerCommissionTestCase):
	"""Users can pick which Sales Invoices to pay commission on."""

	def setUp(self):
		super().setUp()
		commission.ensure_partner_supplier(self.partner.name)
		self.other = make_partner("PC Second Partner", rate=5)
		commission.ensure_partner_supplier(self.other.name)

	def bill(self, sales_invoices):
		return commission.make_all_commission_purchase_invoices(COMPANY, sales_invoices=sales_invoices)

	def test_only_the_selected_invoices_are_billed(self):
		first, second, third = self.invoice(1000), self.invoice(500), self.invoice(200)
		result = self.bill([first.name, third.name])

		pi = frappe.get_doc("Purchase Invoice", result["created"][0]["purchase_invoice"])
		self.assertEqual(sorted(row.rate for row in pi.items), [20, 100])
		self.assertEqual([r.name for r in self.payable()], [second.name])

	def test_a_selection_across_partners_makes_one_bill_each(self):
		mine, theirs = self.invoice(1000), self.invoice(1000, partner=self.other)
		result = self.bill([mine.name, theirs.name])
		self.assertEqual(
			sorted(row["sales_partner"] for row in result["created"]),
			sorted([self.partner.name, self.other.name]),
		)

	def test_selected_invoices_that_are_not_payable_are_reported(self):
		frappe.db.set_single_value("Selling Settings", "custom_commission_payable_on", "Paid Invoices")
		paid, unpaid = self.invoice(1000), self.invoice(500)
		frappe.db.set_value("Sales Invoice", paid.name, "outstanding_amount", 0)

		result = self.bill([paid.name, unpaid.name])
		self.assertEqual(len(result["created"]), 1)
		self.assertEqual([row.get("sales_invoice") for row in result["skipped"]], [unpaid.name])

		again = self.bill([paid.name])  # already billed now
		self.assertEqual(
			(again["created"], [row.get("sales_invoice") for row in again["skipped"]]), ([], [paid.name])
		)
