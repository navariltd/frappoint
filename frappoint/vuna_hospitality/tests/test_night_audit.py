"""F8 Night audit (minimal)."""

from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from frappoint.vuna_hospitality.api import night_audit as night_audit_api
from frappoint.vuna_hospitality.services import night_audit
from frappoint.vuna_hospitality.services.feature_flag import HospitalityDisabledError
from frappoint.vuna_hospitality.services.folio import CheckOutBalanceError
from frappoint.vuna_hospitality.services.front_desk import assign_room, check_in, check_out, register_guest
from frappoint.vuna_hospitality.services.night_audit import (
	NightAuditRunningError,
	execute_run,
	start_night_audit,
)
from frappoint.vuna_hospitality.services.reservations import confirm, hold
from frappoint.vuna_hospitality.tests.test_folio import make_user
from frappoint.vuna_hospitality.tests.test_reservations import make_booking_fixtures, stay_request
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled


class NightAuditTestCase(IntegrationTestCase):
	CODE = "NAU"

	def setUp(self):
		frappe.db.savepoint("night_audit_test")
		self.prop, self.plan, self.guest = make_booking_fixtures(self.CODE, rooms=3)
		self.today = getdate(self.prop.business_date)
		self.next_room = 101

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="night_audit_test")

	@contextmanager
	def job_context(self, job_active=False):
		"""Run the audit in this test's transaction: no queue, and no commits."""
		with (
			hospitality_enabled(True),
			patch.object(frappe, "enqueue"),
			patch.object(frappe.db, "commit"),
			patch.object(night_audit, "is_job_enqueued", return_value=job_active),
		):
			yield

	def audit(self) -> tuple[str, str]:
		with self.job_context():
			name = start_night_audit(self.CODE)
			return name, execute_run(name)

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
		assign_room(stay.name, f"{self.CODE}-{self.next_room}")
		self.next_room += 1
		for guest in frappe.get_all("Stay Guest", filters={"stay_reservation": stay.name}, pluck="name"):
			register_guest(guest)
		check_in(stay.name)
		return frappe.get_doc("Stay Reservation", stay.name)

	def room_charges(self, stay):
		return frappe.get_all(
			"Folio Transaction",
			filters={"stay_reservation": stay.name, "posting_key": ["like", "night:%"]},
			fields=["posting_key", "gross_amount", "business_date", "service_date"],
			order_by="service_date asc",
		)

	def business_date(self):
		return getdate(frappe.db.get_value("Hotel Property", self.CODE, "business_date"))

	def stage(self, run_name, stage):
		return frappe.db.get_value(
			"Night Audit Run Stage",
			{"parent": run_name, "stage": stage},
			["status", "posted", "skipped", "failed", "message"],
			as_dict=True,
		)


class TestNightlyPosting(NightAuditTestCase):
	def test_three_audits_charge_each_night_once_and_move_the_date(self):
		"""Sprint 5 demo: a 3-night stay, audit run three times, one room charge per night."""
		stay = self.in_house_stay(nights=3)
		folio_name = stay.default_folio
		nights = frappe.get_all(
			"Stay Rate Night",
			filters={"stay_reservation": stay.name},
			fields=["night_date", "total"],
			order_by="night_date",
		)

		for day in range(3):
			name, status = self.audit()
			self.assertEqual(
				(name, status), (f"NA-{self.CODE}-{self.today + timedelta(days=day)}", "Completed")
			)
			self.assertEqual(self.business_date(), self.today + timedelta(days=day + 1))

		charges = self.room_charges(stay)
		self.assertEqual(
			[(getdate(c.service_date), c.gross_amount) for c in charges],
			[(getdate(n.night_date), n.total) for n in nights],
		)
		# Each posting carries the business date its audit closed.
		self.assertEqual(
			[getdate(c.business_date) for c in charges], [getdate(c.service_date) for c in charges]
		)
		self.assertEqual(
			set(
				frappe.get_all(
					"Stay Rate Night", filters={"stay_reservation": stay.name}, pluck="posting_state"
				)
			),
			{"Posted"},
		)
		self.assertEqual(
			frappe.db.get_value("Guest Folio", folio_name, ["balance", "pending_total"]),
			(stay.total_amount, 0),
		)
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "status"), "Due Out")

	def test_a_stay_that_has_not_arrived_is_not_charged(self):
		stay = self.confirmed_stay(nights=2)
		_, status = self.audit()
		self.assertEqual(status, "Completed")
		self.assertEqual(self.room_charges(stay), [])
		message = self.stage(f"NA-{self.CODE}-{self.today}", night_audit.ROLL_STATUSES).message
		self.assertIn(stay.name, message)  # listed as a no-show candidate

	def test_a_zero_rate_night_is_waived_not_posted(self):
		stay = self.in_house_stay(nights=1)
		frappe.db.set_value("Stay Rate Night", {"stay_reservation": stay.name}, "total", 0)
		self.audit()
		self.assertEqual(self.room_charges(stay), [])
		self.assertEqual(
			frappe.db.get_value("Stay Rate Night", {"stay_reservation": stay.name}, "posting_state"), "Waived"
		)


class TestStatusRoll(NightAuditTestCase):
	def test_arrivals_become_due_in_and_departures_due_out(self):
		arriving = self.confirmed_stay(nights=1, arrival=self.today + timedelta(days=1))
		leaving = self.in_house_stay(nights=1)
		staying = self.in_house_stay(nights=3)
		self.audit()
		status = lambda stay: frappe.db.get_value("Stay Reservation", stay.name, "status")  # noqa: E731
		self.assertEqual(
			(status(arriving), status(leaving), status(staying)), ("Due In", "Due Out", "In House")
		)
		self.assertEqual(self.stage(f"NA-{self.CODE}-{self.today}", night_audit.ROLL_STATUSES).posted, 2)


class TestRestart(NightAuditTestCase):
	def posting_fails_on_the_second_night(self, error):
		real = night_audit.post_room_night
		calls = []

		def flaky(name, business_date=None):
			calls.append(name)
			if len(calls) == 2:
				raise error
			return real(name, business_date)

		return patch.object(night_audit, "post_room_night", side_effect=flaky)

	def test_a_failed_run_restarts_and_posts_nothing_twice(self):
		"""Scenario 36: restarting an audit that stopped mid-posting creates no duplicate."""
		stays = [self.in_house_stay(nights=2), self.in_house_stay(nights=2)]
		with self.job_context(), self.posting_fails_on_the_second_night(RuntimeError("database went away")):
			name = start_night_audit(self.CODE)
			self.assertEqual(execute_run(name), "Failed")
		stage = self.stage(name, night_audit.POST_ROOM_CHARGES)
		self.assertEqual((stage.status, stage.posted, stage.failed), ("Failed", 1, 1))
		self.assertIn("database went away", stage.message)
		self.assertEqual(self.business_date(), self.today)  # the day is not closed

		with self.job_context():
			self.assertEqual(start_night_audit(self.CODE), name)
			self.assertEqual(execute_run(name), "Completed")
		for stay in stays:
			self.assertEqual(len(self.room_charges(stay)), 1)
		run = frappe.get_doc("Night Audit Run", name)
		self.assertEqual((run.attempts, run.status), (2, "Completed"))
		self.assertEqual(self.business_date(), self.today + timedelta(days=1))

	def test_a_run_whose_worker_died_is_restarted(self):
		"""Kill the run mid-batch (the worker exits), then restart it."""
		stays = [self.in_house_stay(nights=2), self.in_house_stay(nights=2)]
		with self.job_context(), self.posting_fails_on_the_second_night(SystemExit("worker killed")):
			name = start_night_audit(self.CODE)
			with self.assertRaises(SystemExit):
				execute_run(name)
		self.assertEqual(frappe.db.get_value("Night Audit Run", name, "status"), "Running")

		with self.job_context(job_active=False):
			start_night_audit(self.CODE)
			self.assertEqual(execute_run(name), "Completed")
		for stay in stays:
			self.assertEqual(len(self.room_charges(stay)), 1)
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log", {"reference_name": name, "event_type": "Night Audit Failed"}
			)
		)

	def test_a_live_run_cannot_be_started_again(self):
		with self.job_context():
			start_night_audit(self.CODE)
		with self.job_context(job_active=True), self.assertRaises(NightAuditRunningError):
			start_night_audit(self.CODE)

	def test_runs_are_only_created_by_the_service(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{"doctype": "Night Audit Run", "property": self.CODE, "business_date": self.today}
			).insert(ignore_permissions=True)


class TestCheckOutPostsUsedNights(NightAuditTestCase):
	def test_leaving_on_the_arrival_day_charges_the_first_night_once(self):
		stay = self.in_house_stay(nights=2)
		with self.assertRaises(CheckOutBalanceError):
			check_out(stay.name)
		check_out(stay.name, override_reason="Pays at the desk")
		charges = self.room_charges(stay)
		self.assertEqual([getdate(c.service_date) for c in charges], [self.today])

		# Tonight's audit finds the night already posted and charges nothing more.
		self.audit()
		self.assertEqual(len(self.room_charges(stay)), 1)


class TestNightAuditApi(NightAuditTestCase):
	def test_only_night_audit_roles_start_it(self):
		desk = make_user("frappoint-audit-desk@example.com", "Front Desk Agent")
		auditor = make_user("frappoint-auditor@example.com", "Night Auditor")
		with self.job_context():
			frappe.set_user(desk)
			with self.assertRaises(frappe.PermissionError):
				night_audit_api.start_night_audit(self.CODE)
			frappe.set_user(auditor)
			overview = night_audit_api.start_night_audit(self.CODE)
		self.assertEqual((overview["run"]["status"], overview["can_start"]), ("Queued", True))
		self.assertEqual(len(overview["run"]["stages"]), 4)

	def test_overview_previews_tonight(self):
		stay = self.in_house_stay(nights=2)
		with hospitality_enabled(True):
			overview = night_audit_api.get_night_audit(self.CODE)
		night = frappe.db.get_value(
			"Stay Rate Night", {"stay_reservation": stay.name, "night_date": self.today}, "total"
		)
		self.assertEqual(overview["preview"]["room_nights"], 1)
		self.assertEqual(overview["preview"]["room_charges"], night)
		self.assertIsNone(overview["run"])

	def test_endpoints_and_job_stop_while_hospitality_is_off(self):
		with hospitality_enabled(False), self.assertRaises(HospitalityDisabledError):
			night_audit_api.start_night_audit(self.CODE)
		with self.job_context():
			name = start_night_audit(self.CODE)
		with patch.object(frappe.db, "commit"), hospitality_enabled(False):
			self.assertEqual(execute_run(name), "Failed")
		self.assertEqual(self.business_date(), self.today)
