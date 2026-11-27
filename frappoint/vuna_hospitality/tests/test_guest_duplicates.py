"""Duplicate guest profiles: review, audited merge, and unmerge."""

import frappe
from frappe.tests import IntegrationTestCase

from frappoint.vuna_hospitality.api import guests as guests_api
from frappoint.vuna_hospitality.services import guest_dedup, preferences
from frappoint.vuna_hospitality.services.reservations import confirm, hold
from frappoint.vuna_hospitality.tests.test_reservations import make_booking_fixtures, stay_request
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled

CODE = "DUP"


def profile(first_name, last_name=f"Test{CODE}", **fields) -> str:
	return (
		frappe.get_doc(
			{"doctype": "Guest Profile", "first_name": first_name, "last_name": last_name, **fields}
		)
		.insert(ignore_permissions=True)
		.name
	)


def as_user(email, *roles):
	frappe.set_user("Administrator")  # only an administrator creates users and gives roles
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(*roles)
	frappe.set_user(email)


class DuplicateTestCase(IntegrationTestCase):
	def setUp(self):
		frappe.db.savepoint("duplicate_test")
		self._hospitality = hospitality_enabled(True)
		self._hospitality.__enter__()
		# The site may hold look-alikes of its own; these tests look only at their own profiles.
		self.prop, self.plan, _guest = make_booking_fixtures(CODE, rooms=2)

	def tearDown(self):
		frappe.set_user("Administrator")
		self._hospitality.__exit__(None, None, None)
		frappe.db.rollback(save_point="duplicate_test")

	def pair(self, first, second):
		return frappe.db.get_value(
			guest_dedup.DUPLICATE,
			{"pair_key": guest_dedup.pair_key(first, second)},
			["name", "basis", "strength", "status"],
			as_dict=True,
		)

	def stay_for(self, guest):
		summary = hold(
			CODE,
			[stay_request(CODE, self.plan, frappe._dict(name=guest), self.prop.business_date, 1)],
			booking_details={"booking_source": "Phone Calls"},
		)
		confirm(summary["stays"][0]["name"])
		return summary["stays"][0]["name"]


class TestFindingDuplicates(DuplicateTestCase):
	def test_strong_and_possible_matches_are_proposed_once(self):
		"""Similar names never auto-merge; the match says what it rests on."""
		amina = profile("Amina", email="amina.dup@example.com")
		amina_again = profile("A.", "Otieno", email="AMINA.DUP@example.com")
		phone_a = profile("Brian", mobile_no="0712 345 999")
		phone_b = profile("Bryan", mobile_no="+254712345999")
		born_a = profile("Cate", date_of_birth="1990-01-02")
		born_b = profile("Cate", date_of_birth="1990-01-02")
		name_a = profile("Daudi")
		name_b = profile("Daudi")

		guest_dedup.propose_duplicates()
		match = self.pair(amina, amina_again)
		self.assertEqual((match.basis, match.strength), ("Email", "Strong"))
		self.assertEqual(self.pair(phone_a, phone_b).basis, "Phone")
		self.assertEqual(self.pair(born_a, born_b).basis, "Name and Date of Birth")
		self.assertEqual(
			(self.pair(name_a, name_b).basis, self.pair(name_a, name_b).strength), ("Name Only", "Possible")
		)
		for name in (amina, amina_again, name_a, name_b):
			self.assertFalse(frappe.db.get_value("Guest Profile", name, "merged_into"))

		before = frappe.db.count(guest_dedup.DUPLICATE)
		guest_dedup.propose_duplicates()
		self.assertEqual(frappe.db.count(guest_dedup.DUPLICATE), before)

	def test_a_pair_said_to_be_different_people_is_not_proposed_again(self):
		first, second = profile("Esther"), profile("Esther")
		guest_dedup.propose_duplicates()
		guest_dedup.not_duplicate(self.pair(first, second).name, "Mother and daughter")
		guest_dedup.propose_duplicates()
		self.assertEqual(self.pair(first, second).status, "Not Duplicate")


class TestMerging(DuplicateTestCase):
	def test_a_privileged_merge_moves_everything_keeps_evidence_and_can_be_undone(self):
		"""Profile duplicate: a privileged merge shows the match evidence and keeps an audit."""
		kept = profile("Faith", email="faith.dup@example.com")
		away = profile("Faith", email="faith.dup@example.com", mobile_no="0799111222")
		stay = self.stay_for(away)
		# Flagged after the booking (a restricted guest can't be booked).
		frappe.db.set_value(
			"Guest Profile", away, {"restriction_flag": 1, "restriction_reason": "Unpaid bill"}
		)
		preferences.add_preference(away, "Dietary", "Vegetarian")
		guest_dedup.propose_duplicates()
		duplicate = self.pair(kept, away).name

		as_user("hsp-dup-agent@example.com", "Guest Services Agent")
		comparison = guests_api.compare_duplicate_guests(duplicate)
		self.assertEqual(comparison["basis"], "Email")
		self.assertEqual({row["name"]: row["stays"] for row in comparison["profiles"]}[away], 1)
		with self.assertRaises(frappe.PermissionError):
			guests_api.merge_guests(duplicate, kept, "Same guest")

		as_user("hsp-dup-manager@example.com", "Front Desk Manager")
		with self.assertRaises(frappe.ValidationError):
			guests_api.merge_guests(duplicate, kept, " ")
		merge = guests_api.merge_guests(duplicate, kept, "Same email, same phone at check-in")["merge"]

		self.assertEqual(frappe.db.get_value("Guest Profile", away, "merged_into"), kept)
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay, "lead_guest"), kept)
		self.assertTrue(frappe.db.exists("Stay Guest", {"stay_reservation": stay, "guest_profile": kept}))
		self.assertTrue(frappe.db.exists("Guest Preference", {"guest_profile": kept, "value": "Vegetarian"}))
		filled = frappe.db.get_value("Guest Profile", kept, ["mobile_no", "restriction_flag"], as_dict=True)
		self.assertEqual(
			(filled.mobile_no, filled.restriction_flag), ("0799111222", 1)
		)  # the do-not-rent flag survives
		record = frappe.get_doc(guest_dedup.MERGE, merge)
		self.assertEqual((record.basis, record.merged_by), ("Email", "hsp-dup-manager@example.com"))
		self.assertIn("Same email", record.evidence)
		self.assertEqual(self.pair(kept, away).status, "Merged")
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log", {"reference_name": away, "event_type": "Guest Profiles Merged"}
			)
		)

		guests_api.unmerge_guests(merge, "Different people after all")
		self.assertFalse(frappe.db.get_value("Guest Profile", away, "merged_into"))
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay, "lead_guest"), away)
		self.assertTrue(frappe.db.exists("Guest Preference", {"guest_profile": away, "value": "Vegetarian"}))
		self.assertFalse(frappe.db.get_value("Guest Profile", kept, "mobile_no"))
		self.assertEqual(frappe.db.get_value(guest_dedup.MERGE, merge, "status"), "Unmerged")
		self.assertEqual(self.pair(kept, away).status, "Not Duplicate")

	def test_merged_profiles_leave_search_and_earlier_merges_follow(self):
		first, second, third = (
			profile("Grace", email="grace.dup@example.com"),
			profile("Grace", email="grace.dup@example.com"),
			profile("Grace", email="grace.dup@example.com"),
		)
		guest_dedup.merge(third, second, "Same guest")
		guest_dedup.merge(second, first, "Same guest")
		# The profile merged into `second` earlier now points at the one kept.
		self.assertEqual(frappe.db.get_value("Guest Profile", third, "merged_into"), first)
		found = {row["name"] for row in guests_api.search_guests("grace.dup@example.com")}
		self.assertEqual(found, {first})
		with self.assertRaises(guest_dedup.MergeError):
			guest_dedup.merge(second, first, "Again")
