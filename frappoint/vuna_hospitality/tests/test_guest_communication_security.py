"""F20 Guest communication, guest register, and security."""

import importlib
from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.email.doctype.email_account.email_account import EmailAccount
from frappe.utils import add_days, getdate, now_datetime

from frappoint.vuna_hospitality.api import folios as folio_api
from frappoint.vuna_hospitality.api import front_desk as front_desk_api
from frappoint.vuna_hospitality.api import guest_communication as communication_api
from frappoint.vuna_hospitality.api import guest_register as register_api
from frappoint.vuna_hospitality.api import housekeeping as housekeeping_api
from frappoint.vuna_hospitality.api import night_audit as night_audit_api
from frappoint.vuna_hospitality.api import quote as quote_api
from frappoint.vuna_hospitality.api import services as services_api
from frappoint.vuna_hospitality.services import (
	data_retention,
	front_desk,
	guest_messages,
	guest_register,
	notifications,
)
from frappoint.vuna_hospitality.services.front_desk import (
	add_stay_guest,
	assign_room,
	change_departure,
	check_in,
	register_guest,
)
from frappoint.vuna_hospitality.services.guests import reveal_id_document
from frappoint.vuna_hospitality.tests.test_folio import FolioTestCase
from frappoint.vuna_hospitality.tests.test_guest_profiles import make_user
from frappoint.vuna_hospitality.tests.test_reservations import make_booking_fixtures, stay_request
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled

LOG = "Guest Notification Log"
TEMPLATE = "HSP Test Confirmation"


def email_template(
	name=TEMPLATE, subject="Booking {{ stay.name }}", body="Dear {{ guest.first_name }}"
) -> str:
	if not frappe.db.exists("Email Template", name):
		frappe.get_doc(
			{"doctype": "Email Template", "name": name, "subject": subject, "response": body}
		).insert(ignore_permissions=True)
	return name


def as_user(email: str, *roles: str) -> str:
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
		user.add_roles(*roles)
	else:
		make_user(email, list(roles))
	frappe.set_user(email)
	return email


class GuestCareTestCase(FolioTestCase):
	CODE = "GCS"

	def setUp(self):
		super().setUp()
		self._hospitality = hospitality_enabled(True)
		self._hospitality.__enter__()
		# Email is only queued, but queuing needs an outgoing account; a fresh test site has none.
		self._outgoing = patch.object(EmailAccount, "find_outgoing", return_value=EmailAccount.create_dummy())
		self._outgoing.start()
		frappe.db.set_value(
			"Guest Profile",
			self.guest.name,
			{"email": "hsp-gcs-guest@example.com", "mobile_no": "0712000999"},
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		self._outgoing.stop()
		self._hospitality.__exit__(None, None, None)
		super().tearDown()

	def rule(self, event, channel="Email", **fields):
		doc = frappe.get_doc(
			{
				"doctype": "Guest Notification Rule",
				"property": self.prop.name,
				"rule_name": f"{event} {channel} {frappe.generate_hash(length=4)}",
				"event": event,
				"channel": channel,
				"recipient_role": fields.pop("recipient_role", "Primary Guest"),
				"email_template": email_template() if channel == "Email" else None,
				"sms_message": "Hi {{ guest.first_name }}, see you {{ stay.arrival_date }}"
				if channel == "SMS"
				else None,
				**fields,
			}
		).insert(ignore_permissions=True)
		return doc.name

	def logs(self, **filters):
		return frappe.get_all(
			LOG,
			filters=filters,
			fields=["rule", "status", "recipient", "communication", "error", "guest_profile"],
		)


class TestNotifications(GuestCareTestCase):
	def test_a_confirmation_is_emailed_once_and_logged_on_both_timelines(self):
		rule = self.rule(notifications.BOOKING_CONFIRMED)
		stay = self.confirmed_stay()
		logs = self.logs(rule=rule)
		self.assertEqual(
			[(row.status, row.recipient) for row in logs], [("Sent", "hsp-gcs-guest@example.com")]
		)
		comm = frappe.get_doc("Communication", logs[0].communication)
		self.assertEqual((comm.reference_doctype, comm.reference_name), ("Stay Reservation", stay.name))
		self.assertIn("Dear Wanjiku", comm.content)
		self.assertIn(self.guest.name, [link.link_name for link in comm.timeline_links])

		# The same event again sends nothing more.
		notifications.dispatch(notifications.BOOKING_CONFIRMED, stay=stay.name)
		self.assertEqual(len(self.logs(rule=rule)), 1)

	def test_sms_marketing_consent_and_language(self):
		sms = self.rule(notifications.BOOKING_CONFIRMED, "SMS")
		marketing = self.rule(notifications.BOOKING_CONFIRMED, purpose="Marketing")
		french = self.rule(notifications.BOOKING_CONFIRMED, language="fr")
		with patch("frappe.core.doctype.sms_settings.sms_settings.send_sms") as send:
			self.confirmed_stay()
		send.assert_called_once()
		self.assertEqual(send.call_args.args[0], ["0712000999"])
		self.assertTrue(send.call_args.args[1].startswith("Hi Wanjiku"))
		self.assertEqual([row.status for row in self.logs(rule=sms)], ["Sent"])
		# Marketing needs consent, and a French rule is only for French-speaking guests.
		self.assertEqual([row.status for row in self.logs(rule=marketing)], ["Skipped"])
		self.assertEqual(self.logs(rule=french), [])

		frappe.db.set_value("Guest Profile", self.guest.name, "language", "fr")
		with patch("frappe.core.doctype.sms_settings.sms_settings.send_sms"):
			self.confirmed_stay()
		self.assertEqual(len(self.logs(rule=french)), 1)

	def test_a_failed_send_never_fails_the_command(self):
		rule = self.rule(notifications.BOOKING_CONFIRMED, "SMS")
		with patch(
			"frappe.core.doctype.sms_settings.sms_settings.send_sms",
			side_effect=frappe.ValidationError("No SMS gateway"),
		):
			stay = self.confirmed_stay()
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "status"), "Confirmed")
		self.assertEqual(
			[(row.status, row.error) for row in self.logs(rule=rule)], [("Failed", "No SMS gateway")]
		)

	def test_timed_reminders_and_amendments_send_per_occurrence(self):
		before = self.rule(notifications.BEFORE_ARRIVAL, offset=2)
		amended = self.rule(notifications.BOOKING_AMENDED)
		stay = self.confirmed_stay(nights=2, arrival=self.today + timedelta(days=2))
		# The job covers every property's rules; count only this rule's sends.
		notifications.send_timed()
		self.assertEqual(len(self.logs(rule=before)), 1)
		notifications.send_timed()
		self.assertEqual(len(self.logs(rule=before)), 1)

		change_departure(stay.name, add_days(stay.departure_date, 1))
		change_departure(stay.name, add_days(stay.departure_date, 2))
		self.assertEqual(len(self.logs(rule=amended)), 2)

	def test_a_folio_goes_only_to_its_payee(self):
		stay = self.in_house_stay()
		self.massage(self.folio_of(stay))
		rule = self.rule(notifications.FOLIO_EMAILED, recipient_role="Payee")
		folio = self.folio_of(stay)
		frappe.db.set_value("Guest Folio", folio, "payee_guest_profile", self.guest.name)
		notifications.email_folio(folio)
		logs = self.logs(rule=rule)
		self.assertEqual([row.status for row in logs], ["Sent"])
		# The email belongs to the folio and carries its Information Folio print as a PDF.
		comm = frappe.get_doc("Communication", logs[0].communication)
		self.assertEqual((comm.reference_doctype, comm.reference_name), ("Guest Folio", folio))
		self.assertIn(stay.name, [link.link_name for link in comm.timeline_links])
		queue = frappe.get_doc("Email Queue", {"communication": comm.name})
		attachments = frappe.parse_json(queue.attachments or "[]")
		self.assertEqual([item.get("print_format") for item in attachments], ["Information Folio"])

		companion = frappe._dict(key="x", guest_profile="someone-else", first_name="Amani", full_name="Amani")
		stay_row = notifications._stay(stay.name)
		context = notifications.message_context(companion, stay_row, None, folio)
		self.assertIsNone(context["folio"])
		payee = notifications._profile_recipient(self.guest.name)
		self.assertTrue(notifications.message_context(payee, stay_row, None, folio)["folio"]["lines"])


class TestGuestRegister(GuestCareTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.set_value("Hotel Property", self.prop.name, "guest_register_required", 1)
		self.home = frappe.get_cached_value("Company", self.prop.company, "country")
		self.abroad = "Germany" if self.home != "Germany" else "France"

	def ready_stay(self):
		stay = self.confirmed_stay()
		assign_room(stay.name, f"{self.CODE}-101")
		return stay, frappe.db.get_value(
			"Stay Guest", {"stay_reservation": stay.name, "role": "Primary"}, "name"
		)

	def give_id(self, nationality):
		profile = frappe.get_doc("Guest Profile", self.guest.name)
		profile.update(
			{"nationality": nationality, "id_document_type": "Passport", "id_document_number": "C01234567"}
		)
		profile.save(ignore_permissions=True)

	def test_check_in_needs_the_register_details_and_keeps_a_masked_snapshot(self):
		stay, primary = self.ready_stay()
		register_guest(primary)
		with self.assertRaises(guest_register.RegisterIncompleteError):
			check_in(stay.name)

		self.give_id(self.abroad)
		with self.assertRaises(guest_register.RegisterIncompleteError) as refused:
			check_in(stay.name)
		self.assertIn("Arrived From", str(refused.exception))
		register_guest(
			primary, arrived_from="Frankfurt", next_destination="Mombasa", acceptance_reference="Card 001"
		)
		check_in(stay.name)

		entry = frappe.get_doc("Guest Register Entry", {"stay_guest": primary})
		self.assertEqual(
			(entry.nationality_class, entry.id_document_hint, entry.arrived_from, entry.room_number),
			("Foreign", "•••• 4567", "Frankfurt", "101"),
		)
		self.assertNotEqual(entry.id_document_number, "C01234567")  # stored encrypted

		as_user("hsp-gcs-agent@example.com", "Front Desk Agent")
		with self.assertRaises(frappe.PermissionError):
			register_api.reveal_document_number(entry.name)
		as_user("hsp-gcs-manager@example.com", "Front Desk Manager")
		self.assertEqual(register_api.reveal_document_number(entry.name)["id_document_number"], "C01234567")
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log", {"reference_name": entry.name, "event_type": "Sensitive Data Viewed"}
			)
		)

	def test_residents_give_less_and_the_export_is_restricted_and_recorded(self):
		stay, primary = self.ready_stay()
		self.give_id(self.home)
		register_guest(primary)
		check_in(stay.name)
		self.assertEqual(
			frappe.db.get_value("Guest Register Entry", {"stay_guest": primary}, "nationality_class"),
			"Resident",
		)

		as_user("hsp-gcs-agent@example.com", "Front Desk Agent")
		with self.assertRaises(frappe.PermissionError):
			guest_register.export(self.prop.name, self.today, self.today)
		as_user("hsp-gcs-hm@example.com", "Hospitality Manager")
		rows = guest_register.export(self.prop.name, self.today, self.today)
		self.assertEqual([row["id_document_number"] for row in rows], ["C01234567"])
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log",
				{"reference_name": self.prop.name, "event_type": "Guest Register Exported"},
			)
		)

		# The register keeps its snapshot when the profile's ID is later removed.
		frappe.set_user("Administrator")
		data_retention.purge(self.guest.name)
		self.assertFalse(frappe.db.get_value("Guest Profile", self.guest.name, "id_document_hint"))
		self.assertEqual(
			frappe.db.get_value("Guest Register Entry", {"stay_guest": primary}, "id_document_hint"),
			"•••• 4567",
		)


class TestMessagesAndTraces(GuestCareTestCase):
	def test_messages_wait_on_front_desk_until_delivered_and_traces_reach_their_department(self):
		stay = self.in_house_stay()
		guest_messages.take_message(stay.name, "Your driver is at the gate", sender="Kamau Tours")
		trace = guest_messages.add_trace(stay.name, "Housekeeping", self.today, "Anniversary cake at 7pm")

		today = front_desk.front_desk_today(self.prop.name)
		row = next(row for row in today["in_house"] if row.name == stay.name)
		self.assertEqual((row["pending_messages"], row["open_traces"]), (1, 1))
		self.assertEqual([t.name for t in today["traces_due"]], [trace])
		self.assertEqual(
			[t.name for t in guest_messages.traces_due(self.prop.name, self.today, "Housekeeping")], [trace]
		)

		message = guest_messages.stay_messages(stay.name)["messages"][0]
		with self.assertRaises(frappe.ValidationError):
			guest_messages.close_message(message.name, delivered=False)
		guest_messages.close_message(message.name, channel="In Person")

		as_user("hsp-gcs-hk@example.com", "Housekeeping Supervisor")
		with self.assertRaises(frappe.PermissionError):
			guest_messages.take_message(stay.name, "Hello")
		guest_messages.close_trace(trace, notes="Cake placed")
		frappe.set_user("Administrator")
		row = next(
			row for row in front_desk.front_desk_today(self.prop.name)["in_house"] if row.name == stay.name
		)
		self.assertEqual((row["pending_messages"], row["open_traces"]), (0, 0))


class TestPrivacy(GuestCareTestCase):
	def test_a_companion_is_seen_as_an_occupant_but_not_their_identity_services_or_folio(self):
		"""Privacy: an occupant is visible; their identity, restricted notes, personal services and
		folio are not, without permission."""
		stay = self.in_house_stay()
		self.massage(self.folio_of(stay))
		companion = frappe.get_doc(
			{
				"doctype": "Guest Profile",
				"first_name": "Amani",
				"last_name": f"Test{self.CODE}",
				"id_document_type": "Passport",
				"id_document_number": "P7654321",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Stay Reservation", stay.name, "adults", 1)
		with patch("frappoint.vuna_hospitality.services.front_desk._check_capacity"):
			add_stay_guest(stay.name, companion.name)

		as_user("hsp-gcs-res@example.com", "Reservations Agent")
		details = front_desk_api.get_stay(stay.name)
		self.assertIn("Amani TestGCS", [guest.guest_name for guest in details["guests"]])
		self.assertEqual((details["folios"], details["services"]), ([], []))
		self.assertFalse(details["actions"]["can_view_personal"])
		self.assertIsNone(details["open_balance"])
		with self.assertRaises(frappe.PermissionError):
			services_api.get_stay_services(stay.name)
		with self.assertRaises(frappe.PermissionError):
			reveal_id_document(companion.name)
		profile = frappe.get_doc("Guest Profile", companion.name)
		# Identity details (permlevel 1) stay hidden. The do-not-rent flag (permlevel 2) is meant to
		# be readable by reservations, so they can refuse a restricted guest.
		self.assertFalse(profile.has_permlevel_access_to("date_of_birth", permission_type="read"))
		self.assertFalse(profile.has_permlevel_access_to("id_document_number", permission_type="read"))

		as_user("hsp-gcs-desk@example.com", "Front Desk Agent")
		details = front_desk_api.get_stay(stay.name)
		self.assertTrue(details["folios"])
		self.assertTrue(details["actions"]["can_view_personal"])


class TestPropertyIsolation(GuestCareTestCase):
	REPORTS = (
		"front_desk_movements",
		"guest_ledger",
		"open_folio_balances",
		"deposits_held",
		"cashier_report",
		"charges_and_adjustments",
		"settlement_pending_folios",
		"occupancy_and_revenue",
		"house_position",
		"guest_register",
	)

	def test_a_user_of_one_property_cannot_see_search_or_post_to_another(self):
		"""Property isolation: through the desk lists, the APIs and the reports."""
		other_prop, other_plan, other_guest = make_booking_fixtures("GCT", rooms=1)
		other = self.other_stay(other_plan, other_guest, getdate(other_prop.business_date))
		mine = self.confirmed_stay()
		user = as_user(
			"hsp-gcs-iso@example.com",
			"Hospitality Manager",
			"Front Desk Manager",
			"Night Auditor",
			"Hotel Accountant",
			"Housekeeping Supervisor",
		)
		frappe.set_user("Administrator")
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Hotel Property",
				"for_value": self.prop.name,
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=user)
		frappe.set_user(user)

		denied = [
			lambda: front_desk_api.get_stay(other.name),
			lambda: front_desk_api.get_front_desk_today(other_prop.name),
			lambda: front_desk_api.check_in(other.name),
			lambda: folio_api.get_stay_folios(other.name),
			lambda: housekeeping_api.get_housekeeping_board(other_prop.name),
			lambda: night_audit_api.get_night_audit(other_prop.name),
			lambda: quote_api.search_availability(
				other_prop.name, str(self.today), str(self.today + timedelta(days=1)), 2
			),
			lambda: communication_api.take_message(other.name, "Hello"),
			lambda: communication_api.get_traces_due(other_prop.name),
			lambda: register_api.export_guest_register(other_prop.name, str(self.today), str(self.today)),
		]
		for call in denied:
			with self.assertRaises(frappe.PermissionError):
				call()
		for report in self.REPORTS:
			module = importlib.import_module(f"frappoint.vuna_hospitality.report.{report}.{report}")
			with self.assertRaises(frappe.PermissionError, msg=report):
				module.execute({"property": other_prop.name})

		stays = frappe.get_list("Stay Reservation", pluck="name")
		self.assertIn(mine.name, stays)
		self.assertNotIn(other.name, stays)
		for doctype in ("Hospitality Event Log", "Room Type Inventory Day", "Guest Folio"):
			properties = set(frappe.get_list(doctype, pluck="property", limit_page_length=0)) - {None, ""}
			self.assertNotIn(other_prop.name, properties, doctype)
		self.assertTrue(front_desk_api.get_stay(mine.name))

	def other_stay(self, plan, guest, arrival):
		from frappoint.vuna_hospitality.services.reservations import confirm, hold

		summary = hold(
			"GCT",
			[stay_request("GCT", plan, guest, arrival, 1)],
			booking_details={"booking_source": "Phone Calls"},
		)
		confirm(summary["stays"][0]["name"])
		return frappe.get_doc("Stay Reservation", summary["stays"][0]["name"])


class TestIdRetention(GuestCareTestCase):
	def test_id_documents_are_removed_after_the_retention_period_unless_a_stay_is_open(self):
		frappe.db.set_single_value("Hospitality Settings", "id_document_retention_days", 30)
		old = frappe.get_doc(
			{
				"doctype": "Guest Profile",
				"first_name": "Old",
				"last_name": "TestGCS",
				"id_document_type": "Passport",
				"id_document_number": "X1234567",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value(
			"Guest Profile", old.name, "creation", now_datetime() - timedelta(days=40), update_modified=False
		)
		profile = frappe.get_doc("Guest Profile", self.guest.name)
		profile.update({"id_document_type": "Passport", "id_document_number": "Y7654321"})
		profile.save(ignore_permissions=True)
		frappe.db.set_value(
			"Guest Profile",
			self.guest.name,
			"creation",
			now_datetime() - timedelta(days=40),
			update_modified=False,
		)
		self.confirmed_stay()  # an upcoming stay keeps the document

		self.assertEqual(data_retention.purge_expired_id_documents(), 1)
		self.assertEqual(
			frappe.db.get_value("Guest Profile", old.name, ["id_document_type", "id_document_hint"]),
			(None, None),
		)
		self.assertIsNone(
			frappe.get_doc("Guest Profile", old.name).get_password(
				"id_document_number", raise_exception=False
			)
		)
		self.assertEqual(
			frappe.db.get_value("Guest Profile", self.guest.name, "id_document_type"), "Passport"
		)
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log", {"reference_name": old.name, "event_type": "ID Document Removed"}
			)
		)
