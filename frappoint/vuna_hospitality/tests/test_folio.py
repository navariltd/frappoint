"""F7 Folio and posting engine."""

from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from frappoint.vuna_hospitality.api import folios as folio_api
from frappoint.vuna_hospitality.services import folio
from frappoint.vuna_hospitality.services.feature_flag import HospitalityDisabledError
from frappoint.vuna_hospitality.services.folio import (
	CheckOutBalanceError,
	FolioClosedError,
	NoChargeCodeError,
	PostingError,
	post,
	post_manual_charge,
	rebuild_folio_balance,
	resolve_charge_code,
	reverse_transaction,
)
from frappoint.vuna_hospitality.services.front_desk import assign_room, check_in, check_out, register_guest
from frappoint.vuna_hospitality.services.inventory import run_with_inventory_retry
from frappoint.vuna_hospitality.services.reservations import cancel, confirm, hold
from frappoint.vuna_hospitality.tests.test_inventory import _like_mariadb_11_8
from frappoint.vuna_hospitality.tests.test_reservations import make_booking_fixtures, stay_request
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled, run_concurrently

SPA_GROUP = "HSP Test Spa"
MASSAGE_GROUP = "HSP Test Massage"
FACIAL_GROUP = "HSP Test Facial"
ROOM_ITEM = "HSP-TEST-ROOM-NIGHT"


def make_item_group(name: str, parent: str = "All Item Groups", is_group: int = 0) -> str:
	if not frappe.db.exists("Item Group", name):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": name,
				"parent_item_group": parent,
				"is_group": is_group,
			}
		).insert(ignore_permissions=True)
	return name


def make_item(code: str, item_group: str, rate: float = 0) -> str:
	if not frappe.db.exists("Item", code):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": code,
				"item_name": code.replace("HSP-TEST-", "").replace("-", " ").title(),
				"item_group": item_group,
				"stock_uom": "Nos"
				if frappe.db.exists("UOM", "Nos")
				else frappe.db.get_value("UOM", {}, "name"),
				"is_stock_item": 0,
				"standard_rate": rate,
			}
		).insert(ignore_permissions=True)
	return code


def make_code(code: str, item_group: str | None = None, item: str | None = None, **extra):
	return frappe.get_doc(
		{
			"doctype": "Charge Code",
			"code": code,
			"description": f"Test {code}",
			"transaction_type": "Revenue",
			"item_group": item_group,
			"item": item,
			"print_group": "Spa",
			**extra,
		}
	).insert(ignore_permissions=True)


def make_spa_catalog():
	"""Spa (a group) holds Massage and Facial. SPA covers all of Spa; MSG covers Massage only."""
	make_item_group(SPA_GROUP, is_group=1)
	make_item_group(MASSAGE_GROUP, parent=SPA_GROUP)
	make_item_group(FACIAL_GROUP, parent=SPA_GROUP)
	make_item("HSP-TEST-DEEP-TISSUE", MASSAGE_GROUP, rate=4500)
	make_item("HSP-TEST-HYDRA-FACIAL", FACIAL_GROUP, rate=3000)
	make_code("TSPA", item_group=SPA_GROUP)
	make_code("TMSG", item_group=MASSAGE_GROUP)


class FolioTestCase(IntegrationTestCase):
	CODE = "FOL"

	def setUp(self):
		frappe.db.savepoint("folio_test")
		self.prop, self.plan, self.guest = make_booking_fixtures(self.CODE, rooms=2)
		self.today = getdate(self.prop.business_date)
		make_spa_catalog()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="folio_test")

	def confirmed_stay(self, nights=2, arrival=None):
		summary = hold(
			self.CODE,
			[stay_request(self.CODE, self.plan, self.guest, arrival or self.today, nights)],
			booking_details={"booking_source": "Phone Calls"},
		)
		confirm(summary["stays"][0]["name"])
		return frappe.get_doc("Stay Reservation", summary["stays"][0]["name"])

	def in_house_stay(self, nights=2):
		stay = self.confirmed_stay(nights=nights)
		assign_room(stay.name, f"{self.CODE}-101")
		for guest in frappe.get_all("Stay Guest", filters={"stay_reservation": stay.name}, pluck="name"):
			register_guest(guest)
		check_in(stay.name)
		return frappe.get_doc("Stay Reservation", stay.name)

	def folio_of(self, stay):
		return frappe.db.get_value("Stay Reservation", stay.name, "default_folio")

	def totals(self, folio_name):
		return frappe.db.get_value(
			"Guest Folio", folio_name, ["posted_debits", "posted_credits", "balance", "transaction_count"]
		)

	def massage(self, folio_name, request_id=None, quantity=1):
		return post_manual_charge(
			folio_name, "HSP-TEST-DEEP-TISSUE", quantity=quantity, request_id=request_id
		)


class TestChargeCodeCoverage(FolioTestCase):
	def test_fixed_item_wins_then_the_nearest_covering_group(self):
		self.assertEqual(resolve_charge_code(ROOM_ITEM).name, "TROOM")
		self.assertEqual(resolve_charge_code("HSP-TEST-DEEP-TISSUE").name, "TMSG")
		# Facial has no code of its own, so the code covering its parent group posts it.
		self.assertEqual(resolve_charge_code("HSP-TEST-HYDRA-FACIAL").name, "TSPA")

	def test_a_new_item_in_a_covered_group_needs_no_setup(self):
		make_item("HSP-TEST-HOT-STONE", MASSAGE_GROUP, rate=5000)
		self.assertEqual(resolve_charge_code("HSP-TEST-HOT-STONE").name, "TMSG")

	def test_an_item_no_code_covers_is_refused(self):
		make_item_group("HSP Test Laundry")
		make_item("HSP-TEST-SHIRT-PRESS", "HSP Test Laundry", rate=300)
		with self.assertRaises(NoChargeCodeError):
			resolve_charge_code("HSP-TEST-SHIRT-PRESS")

	def test_item_search_offers_only_items_a_code_covers(self):
		make_item_group("HSP Test Laundry")
		make_item("HSP-TEST-SHIRT-PRESS", "HSP Test Laundry", rate=300)
		found = {row.name for row in folio.search_postable_items("HSP-TEST", limit=50)}
		self.assertTrue({"HSP-TEST-DEEP-TISSUE", "HSP-TEST-HYDRA-FACIAL", ROOM_ITEM} <= found)
		self.assertNotIn("HSP-TEST-SHIRT-PRESS", found)

	def test_two_codes_cannot_cover_the_same_group_or_item(self):
		with self.assertRaises(frappe.ValidationError):
			make_code("TSPA2", item_group=SPA_GROUP)
		with self.assertRaises(frappe.ValidationError):
			make_code("TROOM2", item=ROOM_ITEM)

	def test_a_fixed_item_must_sit_inside_the_covered_group(self):
		with self.assertRaises(frappe.ValidationError):
			make_code("TBAD", item_group=MASSAGE_GROUP, item="HSP-TEST-HYDRA-FACIAL")

	def test_the_room_charge_code_needs_a_fixed_item(self):
		self.plan.room_charge_code = "TSPA"
		with self.assertRaises(frappe.ValidationError):
			self.plan.save()


class TestDefaultFolio(FolioTestCase):
	def test_confirming_opens_one_default_folio(self):
		stay = self.confirmed_stay(nights=2)
		folio_name = self.folio_of(stay)
		row = frappe.get_doc("Guest Folio", folio_name)
		self.assertEqual((row.status, row.is_default, row.stay_reservation), ("Open", 1, stay.name))
		self.assertEqual(row.payee_guest_profile, self.guest.name)
		self.assertTrue(folio_name.startswith(f"GF-{self.CODE}-"))
		# The unposted nights show as pending, never in the balance.
		self.assertEqual((row.pending_total, row.balance), (stay.total_amount, 0))

		confirm(stay.name)
		self.assertEqual(folio.ensure_default_folio(stay.name), folio_name)
		self.assertEqual(frappe.db.count("Guest Folio", {"stay_reservation": stay.name}), 1)

	def test_a_held_stay_has_no_folio_yet(self):
		summary = hold(
			self.CODE,
			[stay_request(self.CODE, self.plan, self.guest, self.today)],
			booking_details={"booking_source": "Phone Calls"},
		)
		self.assertFalse(frappe.db.exists("Guest Folio", {"stay_reservation": summary["stays"][0]["name"]}))

	def test_cancelling_closes_an_idle_folio_and_keeps_one_with_charges(self):
		idle = self.confirmed_stay(nights=1)
		cancel(idle.name, "Guest changed plans")
		self.assertEqual(frappe.db.get_value("Guest Folio", self.folio_of(idle), "status"), "Closed")

		charged = self.confirmed_stay(nights=1, arrival=self.today + timedelta(days=5))
		self.massage(self.folio_of(charged))
		cancel(charged.name, "Guest changed plans")
		self.assertEqual(frappe.db.get_value("Guest Folio", self.folio_of(charged), "status"), "Open")

	def test_a_closed_folio_takes_no_postings(self):
		stay = self.confirmed_stay(nights=1)
		cancel(stay.name, "Duplicate booking")
		with self.assertRaises(FolioClosedError):
			self.massage(self.folio_of(stay))


class TestPosting(FolioTestCase):
	def test_the_same_posting_key_posts_once(self):
		"""Plan F7 done-when: posting the same key twice gives one transaction."""
		folio_name = self.folio_of(self.confirmed_stay())
		first = post(folio_name, "TROOM", 10000, posting_key="night:TEST:2026-11-14:room")
		second = post(folio_name, "TROOM", 10000, posting_key="night:TEST:2026-11-14:room")

		self.assertTrue(first["created"])
		self.assertEqual(second, {"name": first["name"], "created": False})
		self.assertEqual(frappe.db.count("Folio Transaction", {"guest_folio": folio_name}), 1)
		self.assertEqual(self.totals(folio_name), (10000, 0, 10000, 1))

	def test_a_duplicate_key_found_only_by_the_index_returns_the_existing_line(self):
		"""Insert first: when the fast-path read misses, the unique index still stops a second line."""
		folio_name = self.folio_of(self.confirmed_stay())
		first = post(folio_name, "TROOM", 10000, posting_key="night:RACE:1")
		with patch.object(folio, "_posted", side_effect=[None, first["name"]]):
			second = post(folio_name, "TROOM", 10000, posting_key="night:RACE:1")
		self.assertEqual(second, {"name": first["name"], "created": False})
		self.assertEqual(self.totals(folio_name), (10000, 0, 10000, 1))
		self.assertFalse([m for m in frappe.local.message_log if "unique" in str(m).lower()])

	def test_staff_post_by_item_and_the_line_keeps_guest_and_room(self):
		stay = self.in_house_stay()
		folio_name = self.folio_of(stay)
		primary = frappe.db.get_value(
			"Stay Guest", {"stay_reservation": stay.name, "role": "Primary"}, "name"
		)
		result = post_manual_charge(folio_name, "HSP-TEST-DEEP-TISSUE", quantity=2, stay_guest=primary)

		line = frappe.get_doc("Folio Transaction", result["name"])
		self.assertEqual((line.docstatus, line.direction, line.charge_code), (1, "Debit", "TMSG"))
		self.assertEqual((line.item, line.item_group), ("HSP-TEST-DEEP-TISSUE", MASSAGE_GROUP))
		self.assertEqual((line.quantity, line.unit_rate, line.gross_amount), (2, 4500, 9000))
		self.assertEqual((line.consumer_guest_profile, line.room_number_snapshot), (self.guest.name, "101"))
		self.assertEqual(getdate(line.business_date), self.today)
		self.assertEqual(line.accounting_mode, "Deferred to Folio Invoice")
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log",
				{"reference_name": folio_name, "event_type": "Debit Posted"},
			)
		)

	def test_a_retried_request_posts_once(self):
		folio_name = self.folio_of(self.confirmed_stay())
		first = self.massage(folio_name, request_id="dialog-1")
		self.assertEqual(self.massage(folio_name, request_id="dialog-1")["name"], first["name"])
		self.assertNotEqual(self.massage(folio_name, request_id="dialog-2")["name"], first["name"])
		self.assertEqual(self.totals(folio_name)[2], 9000)

	def test_a_charge_against_its_direction_needs_allow_negative(self):
		folio_name = self.folio_of(self.confirmed_stay())
		with self.assertRaises(PostingError):
			post(
				folio_name,
				"TMSG",
				500,
				posting_key="discount:1",
				direction="Credit",
				item="HSP-TEST-DEEP-TISSUE",
			)

	def test_amounts_must_be_positive_and_items_must_match_the_code(self):
		folio_name = self.folio_of(self.confirmed_stay())
		with self.assertRaises(PostingError):
			post(folio_name, "TROOM", 0, posting_key="zero:1")
		with self.assertRaises(PostingError):
			post(folio_name, "TMSG", 100, posting_key="wrong-group:1", item="HSP-TEST-HYDRA-FACIAL")
		with self.assertRaises(PostingError):
			post(folio_name, "TSPA", 100, posting_key="no-item:1")


class TestReversal(FolioTestCase):
	def test_a_wrong_charge_is_reversed_with_a_reason(self):
		"""Plan F7 done-when: a wrong charge can be reversed with a reason."""
		folio_name = self.folio_of(self.confirmed_stay())
		charge = self.massage(folio_name)["name"]
		with self.assertRaises(PostingError):
			reverse_transaction(charge, "  ")

		reversal = reverse_transaction(charge, "Posted to the wrong guest")
		line = frappe.get_doc("Folio Transaction", reversal["name"])
		self.assertEqual((line.direction, line.reverses, line.gross_amount), ("Credit", charge, 4500))
		self.assertEqual(line.reason, "Posted to the wrong guest")
		self.assertEqual(self.totals(folio_name), (4500, 4500, 0, 2))
		# The original is untouched and still discoverable.
		self.assertEqual(frappe.db.get_value("Folio Transaction", charge, "docstatus"), 1)

		self.assertEqual(reverse_transaction(charge, "Clicked twice"), {"name": line.name, "created": False})
		with self.assertRaises(PostingError):
			reverse_transaction(line.name, "Undo the undo")

	def test_posted_lines_cannot_be_edited_cancelled_or_deleted(self):
		folio_name = self.folio_of(self.confirmed_stay())
		line = frappe.get_doc("Folio Transaction", self.massage(folio_name)["name"])
		refused = (frappe.ValidationError, frappe.PermissionError)
		line.description_snapshot = "Something else"
		with self.assertRaises(refused):
			line.save()
		with self.assertRaises(refused):
			frappe.get_doc("Folio Transaction", line.name).cancel()
		with self.assertRaises(refused):
			frappe.delete_doc("Folio Transaction", line.name, ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{**line.as_dict(), "name": None, "posting_key": "typed-in:1", "docstatus": 0}
			).insert(ignore_permissions=True)

	def test_folio_totals_are_not_edited_by_hand(self):
		folio_doc = frappe.get_doc("Guest Folio", self.folio_of(self.confirmed_stay()))
		folio_doc.folio_label = "Personal"
		folio_doc.save()
		folio_doc.balance = 1
		with self.assertRaises(frappe.ValidationError):
			folio_doc.save()


class TestBalanceRebuild(FolioTestCase):
	def test_rebuild_matches_the_cached_balance_and_repairs_drift(self):
		"""Plan F7 done-when: balance rebuild matches the cached balance."""
		folio_name = self.folio_of(self.confirmed_stay())
		self.massage(folio_name, quantity=3)
		reverse_transaction(self.massage(folio_name)["name"], "Wrong item")
		clean = rebuild_folio_balance(folio_name)
		self.assertFalse(clean["drift"])
		self.assertEqual(clean["after"]["balance"], 13500)

		frappe.db.set_value("Guest Folio", folio_name, "balance", 1)
		repaired = rebuild_folio_balance(folio_name)
		self.assertTrue(repaired["drift"])
		self.assertEqual(self.totals(folio_name), (18000, 4500, 13500, 3))


class TestCheckOut(FolioTestCase):
	def test_check_out_needs_a_zero_balance_or_a_managers_override(self):
		stay = self.in_house_stay(nights=1)
		folio_name = self.folio_of(stay)
		self.massage(folio_name)
		with self.assertRaises(CheckOutBalanceError):
			check_out(stay.name)

		manager_less = make_user("frappoint-folio-desk@example.com", "Front Desk Agent")
		frappe.set_user(manager_less)
		with self.assertRaises(frappe.PermissionError):
			check_out(stay.name, override_reason="Company will pay")
		frappe.set_user("Administrator")

		check_out(stay.name, override_reason="Company will pay")
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "status"), "Checked Out")
		# The balance (the massage and the first night, posted at check-out) stays open for
		# settlement (F11), and the override is on record.
		self.assertEqual(
			frappe.db.get_value("Guest Folio", folio_name, ["status", "balance"]),
			("Open", 4500 + stay.total_amount),
		)
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log",
				{"reference_name": stay.name, "event_type": "Check-out Balance Override"},
			)
		)

	def test_a_complimentary_stay_with_nothing_to_invoice_closes_its_folio(self):
		stay = self.in_house_stay(nights=1)
		folio_name = self.folio_of(stay)
		# A zero-rate night is waived, not posted, so there is nothing to invoice.
		frappe.db.set_value("Stay Rate Night", {"stay_reservation": stay.name}, "total", 0)
		reverse_transaction(self.massage(folio_name)["name"], "Not ours")
		check_out(stay.name)
		self.assertEqual(frappe.db.get_value("Guest Folio", folio_name, "status"), "Closed")


class TestFolioApi(FolioTestCase):
	def test_workspace_lists_lines_and_marks_reversals(self):
		stay = self.confirmed_stay(nights=2)
		folio_name = self.folio_of(stay)
		charge = self.massage(folio_name)["name"]
		reverse_transaction(charge, "Wrong guest")
		with hospitality_enabled(True):
			details = folio_api.get_stay_folios(stay.name)
		lines = {row.name: row for row in details["folios"][0]["transactions"]}
		self.assertTrue(lines[charge]["reversed_by"])
		self.assertEqual(details["totals"], {"balance": 0, "pending": stay.total_amount})
		self.assertEqual(len(details["pending_nights"]), 2)
		self.assertTrue(details["actions"]["can_reverse"])

	def test_endpoints_refuse_while_hospitality_is_off(self):
		folio_name = self.folio_of(self.confirmed_stay())
		with hospitality_enabled(False), self.assertRaises(HospitalityDisabledError):
			folio_api.post_charge(folio_name, "HSP-TEST-DEEP-TISSUE")

	def test_only_posting_roles_post_and_only_managers_reverse(self):
		folio_name = self.folio_of(self.confirmed_stay())
		charge = self.massage(folio_name)["name"]
		auditor = make_user("frappoint-folio-auditor@example.com", "Night Auditor")
		desk = make_user("frappoint-folio-desk@example.com", "Front Desk Agent")
		with hospitality_enabled(True):
			frappe.set_user(auditor)
			with self.assertRaises(frappe.PermissionError):
				folio_api.post_charge(folio_name, "HSP-TEST-DEEP-TISSUE")
			frappe.set_user(desk)
			posted = folio_api.post_charge(folio_name, "HSP-TEST-DEEP-TISSUE", request_id="api-1")
			self.assertTrue(posted["posted"]["created"])
			with self.assertRaises(frappe.PermissionError):
				folio_api.reverse_transaction(charge, "Not allowed")


class TestConcurrentPosting(IntegrationTestCase):
	"""Racing postings need committed data on separate connections; everything is removed after."""

	CODE = "FOLR"

	def setUp(self):
		self._cleanup()
		self.prop, self.plan, self.guest = make_booking_fixtures(self.CODE, rooms=2)
		make_spa_catalog()
		self.folio, self.other_folio = (self.confirmed_folio() for _ in range(2))
		frappe.db.commit()

	def tearDown(self):
		self._cleanup()

	def _cleanup(self):
		frappe.db.rollback()
		code = self.CODE
		for doctype in (
			"Folio Transaction",
			"Guest Folio",
			"Stay Guest",
			"Stay Rate Night",
			"Occupancy Membership",
			"Stay Reservation",
			"Room Occupancy",
			"Hotel Booking",
			"Room Type Inventory Day",
			"Room Rate Day",
			"Rate Season",
			"Rate Plan",
			"Hotel Policy",
			"Hotel Room",
			"Room Type",
		):
			frappe.db.delete(doctype, {"property": code})
		frappe.db.delete("Rate Season Rate", {"room_type": ["like", f"{code}-%"]})
		frappe.db.delete("Guest Profile", {"last_name": f"Test{code}"})
		frappe.db.delete("Hospitality Event Log", {"property": code})
		frappe.db.delete("Hotel Property", {"name": code})
		for code_name in ("TSPA", "TMSG"):
			frappe.db.delete("Charge Code", {"name": code_name})
		frappe.db.commit()

	def confirmed_folio(self):
		summary = hold(
			self.CODE,
			[stay_request(self.CODE, self.plan, self.guest, getdate(self.prop.business_date))],
			booking_details={"booking_source": "Phone Calls"},
		)
		confirm(summary["stays"][0]["name"])
		return frappe.db.get_value("Stay Reservation", summary["stays"][0]["name"], "default_folio")

	def charge(self, request_id, folio_name=None):
		"""One request as the endpoint runs it: MariaDB 11.6+ locking, retried on a conflict."""

		def run():
			_like_mariadb_11_8()
			return run_with_inventory_retry(
				lambda: post_manual_charge(
					folio_name or self.folio, "HSP-TEST-DEEP-TISSUE", request_id=request_id
				)
			)

		return run

	def test_two_requests_with_one_key_post_one_line(self):
		results = run_concurrently(self.charge("same"), self.charge("same"))
		self.assertTrue(all(r.ok for r in results), [r.error for r in results])
		self.assertEqual(results[0].value["name"], results[1].value["name"])
		self.assertEqual(frappe.db.count("Folio Transaction", {"guest_folio": self.folio}), 1)
		self.assertEqual(frappe.db.get_value("Guest Folio", self.folio, "balance"), 4500)

	def test_two_different_charges_both_count_in_the_balance(self):
		results = run_concurrently(self.charge("one"), self.charge("two"))
		self.assertTrue(all(r.ok for r in results), [r.error for r in results])
		self.assertEqual(
			frappe.db.get_value("Guest Folio", self.folio, ["balance", "transaction_count"]), (9000, 2)
		)
		self.assertFalse(rebuild_folio_balance(self.folio)["drift"])

	def test_postings_to_two_folios_at_once_both_succeed(self):
		"""Postings to different folios don't wait on, or deadlock with, each other."""
		results = run_concurrently(self.charge("a"), self.charge("b", self.other_folio))
		self.assertTrue(all(r.ok for r in results), [r.error for r in results])
		for folio_name in (self.folio, self.other_folio):
			self.assertEqual(frappe.db.get_value("Guest Folio", folio_name, "balance"), 4500)


def make_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": role,
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
	frappe.clear_cache(user=email)
	return email
