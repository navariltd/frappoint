"""F4 Guest profiles (core)."""

from datetime import timedelta

import frappe
from frappe.client import get as client_get
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, today

from frappoint.vuna_hospitality.api.guests import search_guests as search_guests_api
from frappoint.vuna_hospitality.services.feature_flag import HospitalityDisabledError
from frappoint.vuna_hospitality.services.guests import (
	ProvisionalGuestError,
	assert_registrable,
	create_guest,
	get_relationships,
	link_customer,
	normalize_phone,
	reveal_id_document,
	search_guests,
)
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled


def make_guest(first_name="Amina", last_name="Testotieno", **fields):
	return frappe.get_doc(
		{"doctype": "Guest Profile", "first_name": first_name, "last_name": last_name, **fields}
	).insert(ignore_permissions=True)


def make_user(email, roles):
	user = frappe.get_doc(
		{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
	).insert(ignore_permissions=True)
	user.add_roles(*roles)
	return user.name


class GuestTestCase(IntegrationTestCase):
	def setUp(self):
		frappe.db.savepoint("guest_test")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="guest_test")


class TestGuestProfile(GuestTestCase):
	def test_contacts_are_normalized_and_full_name_is_built(self):
		guest = make_guest(
			"  Amina ", " Otieno ", email=" Amina.Otieno@Example.COM ", mobile_no="+254 (712) 345-678"
		)
		self.assertEqual(guest.full_name, "Amina Otieno")
		self.assertEqual(guest.email, "amina.otieno@example.com")
		self.assertEqual(guest.mobile_no, "+254712345678")
		self.assertEqual(normalize_phone("00254 712 345678"), "+254712345678")
		self.assertEqual(normalize_phone("0712-345-678"), "0712345678")

	def test_invalid_contacts_are_refused(self):
		with self.assertRaises(frappe.ValidationError):
			make_guest(email="not-an-email")
		with self.assertRaises(frappe.ValidationError):
			make_guest(mobile_no="12")

	def test_id_number_is_encrypted_and_masked(self):
		guest = make_guest(id_document_type="Passport", id_document_number="AB1234567")
		self.assertEqual(guest.id_document_hint, "•••• 4567")
		self.assertNotIn(
			"AB1234567", str(frappe.db.get_value("Guest Profile", guest.name, "id_document_number"))
		)
		self.assertEqual(guest.get_password("id_document_number"), "AB1234567")

	def test_one_user_per_guest(self):
		make_guest(user="Administrator")
		with self.assertRaises(frappe.ValidationError):
			make_guest("Other", user="Administrator")

	def test_consent_and_restriction_changes_are_logged(self):
		guest = make_guest()
		guest.update({"marketing_consent": 1, "consent_source": "Registration Card"})
		guest.save()
		self.assertTrue(guest.consent_date)
		guest.update({"restriction_flag": 1, "restriction_reason": "Damaged room 204"})
		guest.save()
		events = frappe.get_all(
			"Hospitality Event Log", filters={"reference_name": guest.name}, pluck="event_type"
		)
		self.assertIn("Consent Changed", events)
		self.assertIn("Restriction Set", events)

	def test_restriction_needs_a_reason(self):
		with self.assertRaises(frappe.ValidationError):
			make_guest(restriction_flag=1)


class TestGuestSearchAndCreate(GuestTestCase):
	def setUp(self):
		super().setUp()
		self.amina = make_guest(
			email="amina@f4-test.example", mobile_no="+254799100200", preferred_name="Testmina"
		)
		self.brian = make_guest("Brian", "Kamau", email="brian@f4-test.example")

	def names(self, text):
		return [row["name"] for row in search_guests(text)]

	def test_search_by_email_phone_and_name(self):
		self.assertEqual(self.names("AMINA@f4-test.example"), [self.amina.name])
		self.assertEqual(self.names("0799 100 200"), [self.amina.name])  # local form of the same number
		self.assertEqual(self.names("testotieno amina"), [self.amina.name])
		self.assertEqual(self.names("testmina"), [self.amina.name])  # preferred name
		self.assertEqual(search_guests("brian@f4-test.example")[0]["match"], "Email")

	def test_merged_profiles_are_not_found(self):
		self.brian.db_set("merged_into", self.amina.name)
		self.assertEqual(self.names("brian@f4-test.example"), [])

	def test_create_returns_matches_instead_of_a_duplicate(self):
		result = create_guest("Amina", "O.", mobile_no="0799100200")
		self.assertFalse(result["created"])
		self.assertEqual([row["name"] for row in result["matches"]], [self.amina.name])

		forced = create_guest("Amina", "O.", mobile_no="0799100200", force=True)
		self.assertTrue(forced["created"])

	def test_api_requires_hospitality_enabled(self):
		with hospitality_enabled(False), self.assertRaises(HospitalityDisabledError):
			search_guests_api("testotieno")
		with hospitality_enabled(True):
			self.assertEqual(search_guests_api("testotieno")[0]["name"], self.amina.name)


class TestProvisionalGuest(GuestTestCase):
	def test_provisional_guest_cannot_register_until_completed(self):
		guest = make_guest("Guest of", "Mr Otieno", is_provisional=1)
		with self.assertRaises(ProvisionalGuestError):
			assert_registrable(guest.name)
		guest.update({"first_name": "Zawadi", "last_name": "Otieno", "is_provisional": 0})
		guest.save()
		assert_registrable(guest.name)

	def test_merged_guest_cannot_register(self):
		guest, survivor = make_guest(), make_guest("Amina", "Otieno-Kamau")
		guest.db_set("merged_into", survivor.name)
		with self.assertRaises(frappe.ValidationError):
			assert_registrable(guest.name)


class TestCustomerLink(GuestTestCase):
	def test_create_an_individual_customer(self):
		guest = make_guest(email="amina@f4-test.example")
		customer = link_customer(guest.name)
		self.assertEqual(frappe.db.get_value("Guest Profile", guest.name, "customer"), customer)
		self.assertEqual(
			frappe.db.get_value("Customer", customer, ["customer_name", "customer_type"]),
			("Amina Testotieno", "Individual"),
		)

	def test_one_company_customer_pays_for_many_guests(self):
		company = frappe.db.get_value("Customer", {}, "name") or link_customer(make_guest("Payer").name)
		first, second = make_guest(), make_guest("Brian", "Kamau")
		link_customer(first.name, company)
		link_customer(second.name, company)
		self.assertEqual(
			frappe.db.count(
				"Guest Profile", {"customer": company, "name": ["in", [first.name, second.name]]}
			),
			2,
		)

	def test_provisional_guest_gets_no_customer(self):
		with self.assertRaises(frappe.ValidationError):
			link_customer(make_guest(is_provisional=1).name)


class TestSensitiveFields(GuestTestCase):
	def setUp(self):
		super().setUp()
		self.guest = make_guest(
			date_of_birth="1990-05-01", id_document_type="National ID", id_document_number="12345678"
		)
		self.agent = make_user("f4-reservations@example.com", ["Reservations Agent"])
		self.front_desk = make_user("f4-frontdesk@example.com", ["Front Desk Agent"])

	def test_reservations_agent_cannot_see_identity_fields(self):
		frappe.set_user(self.agent)
		doc = client_get("Guest Profile", self.guest.name)
		self.assertEqual(doc["full_name"], "Amina Testotieno")
		self.assertIsNone(doc.get("date_of_birth"))
		self.assertIsNone(doc.get("id_document_hint"))
		with self.assertRaises(frappe.PermissionError):
			reveal_id_document(self.guest.name)

	def test_front_desk_sees_identity_and_unmasking_is_logged(self):
		frappe.set_user(self.front_desk)
		doc = client_get("Guest Profile", self.guest.name)
		self.assertEqual(str(doc["date_of_birth"]), "1990-05-01")
		self.assertEqual(reveal_id_document(self.guest.name)["id_document_number"], "12345678")
		frappe.set_user("Administrator")
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log",
				{
					"reference_name": self.guest.name,
					"event_type": "Sensitive Data Viewed",
					"user": self.front_desk,
				},
			)
		)

	def test_only_managers_change_the_do_not_rent_flag(self):
		frappe.set_user(self.front_desk)
		guest = frappe.get_doc("Guest Profile", self.guest.name)
		guest.update({"restriction_flag": 1, "restriction_reason": "Unpaid bill"})
		guest.save()
		self.assertEqual(frappe.db.get_value("Guest Profile", guest.name, "restriction_flag"), 0)


class TestGuestRelationship(GuestTestCase):
	def setUp(self):
		super().setUp()
		self.parent, self.child = make_guest(), make_guest("Zawadi", "Otieno")

	def relate(self, guest, related, relationship_type, **fields):
		return frappe.get_doc(
			{
				"doctype": "Guest Relationship",
				"guest_profile": guest.name,
				"related_guest": related.name,
				"relationship_type": relationship_type,
				**fields,
			}
		).insert(ignore_permissions=True)

	def test_relationship_reads_from_both_sides(self):
		self.relate(self.parent, self.child, "Child")
		self.assertEqual(
			[(r["guest"], r["relationship_type"]) for r in get_relationships(self.parent.name)],
			[(self.child.name, "Child")],
		)
		self.assertEqual(
			[(r["guest"], r["relationship_type"]) for r in get_relationships(self.child.name)],
			[(self.parent.name, "Parent")],
		)

	def test_same_relationship_from_the_other_side_is_a_duplicate(self):
		self.relate(self.parent, self.child, "Child")
		with self.assertRaises(frappe.DuplicateEntryError):
			self.relate(self.child, self.parent, "Parent")

	def test_ended_relationships_are_hidden_by_default(self):
		yesterday = getdate(today()) - timedelta(days=1)
		self.relate(self.parent, self.child, "Colleague", valid_to=yesterday)
		self.assertEqual(get_relationships(self.parent.name), [])
		self.assertEqual(len(get_relationships(self.parent.name, include_ended=True)), 1)
		# The old link has ended, so it can be recorded again.
		self.relate(self.parent, self.child, "Colleague", valid_from=today())

	def test_no_self_relationship(self):
		with self.assertRaises(frappe.ValidationError):
			self.relate(self.parent, self.parent, "Spouse/Partner")
