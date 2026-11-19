"""F19 Full night audit and reports."""

from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.utils import flt, getdate

from frappoint.vuna_hospitality.services import (
	audit_checks,
	cashiering,
	folio,
	housekeeping,
	night_audit,
	reconciliation,
)
from frappoint.vuna_hospitality.services.front_desk import (
	CheckOutBlockedError,
	assign_room,
	check_in,
	check_out,
	check_out_blockers,
	register_guest,
)
from frappoint.vuna_hospitality.services.money import from_minor
from frappoint.vuna_hospitality.services.night_audit import NightAuditBlockedError, execute_run
from frappoint.vuna_hospitality.tests.test_cashiering import CASH, CashierTestCase
from frappoint.vuna_hospitality.tests.test_folio import make_user
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled

RUN = "Night Audit Run"


class FullAuditTestCase(CashierTestCase):
	CODE = "FNA"

	@contextmanager
	def job_context(self):
		"""Run the audit in this test's transaction: no queue, and no commits."""
		with (
			hospitality_enabled(True),
			patch.object(frappe, "enqueue"),
			patch.object(frappe.db, "commit"),
			patch.object(night_audit, "is_job_enqueued", return_value=False),
		):
			yield

	def start(self, **overrides) -> str:
		with self.job_context():
			return night_audit.start_night_audit(self.CODE, overrides)

	def audit(self, **overrides) -> tuple[str, str]:
		with self.job_context():
			name = night_audit.start_night_audit(self.CODE, overrides)
			return name, execute_run(name)

	def business_date(self):
		return getdate(frappe.db.get_value("Hotel Property", self.CODE, "business_date"))

	def stage(self, run_name, stage):
		return frappe.db.get_value(
			"Night Audit Run Stage",
			{"parent": run_name, "stage": stage},
			["status", "posted", "skipped", "failed", "message"],
			as_dict=True,
		)

	def as_user(self, role):
		frappe.set_user(make_user(f"hsp-fna-{role.lower().replace(' ', '-')}@example.com", role))

	def settle_with_cash(self, *folios):
		"""Pay every folio's balance in cash and close the shift with the drawer as expected."""
		shift = cashiering.current_shift(self.CODE) or cashiering.open_shift(self.CODE)
		for name in folios:
			balance = flt(frappe.db.get_value("Guest Folio", name, "balance"))
			if balance > 0:
				self.pay(balance, folio_name=name)
		currency = frappe.db.get_value("Cashier Shift", shift, "currency")
		expected = cashiering.expected_totals(shift)
		cashiering.close_shift(
			shift, {mode: from_minor(amount, currency) for mode, amount in expected.items()} or {CASH: 0}
		)

	def night_lines(self, stay_name):
		return frappe.get_all(
			"Folio Transaction",
			filters={"stay_reservation": stay_name, "posting_key": ["like", "night:%"]},
			pluck="posting_key",
		)

	def second_stay(self, nights=1, arrival=None):
		stay = self.confirmed_stay(nights=nights, arrival=arrival)
		assign_room(stay.name, f"{self.CODE}-102")
		for guest in frappe.get_all("Stay Guest", filters={"stay_reservation": stay.name}, pluck="name"):
			register_guest(guest)
		return stay


class TestPreChecks(FullAuditTestCase):
	def test_an_arrival_not_checked_in_blocks_until_the_auditor_lets_it_pass(self):
		stay = self.confirmed_stay(nights=1)
		self.as_user("Night Auditor")
		with self.assertRaises(NightAuditBlockedError):
			self.start()
		self.assertFalse(frappe.db.exists(RUN, night_audit.run_name(self.CODE, self.today)))
		with self.assertRaises(frappe.ValidationError):
			self.start(arrivals="  ")

		name, status = self.audit(arrivals="Guest called: not coming")
		self.assertEqual(status, "Completed")
		override = frappe.get_all(
			"Night Audit Override",
			filters={"parent": name},
			fields=["check_key", "found", "reason", "overridden_by", "role"],
		)
		self.assertEqual(
			[(row.check_key, row.found, row.reason, row.role) for row in override],
			[("arrivals", 1, "Guest called: not coming", "Night Auditor")],
		)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "status"), "No Show")

	def test_open_shifts_need_a_front_desk_manager(self):
		"""Decision D-9: an open cashier shift blocks; only a Front Desk Manager may let it pass."""
		cashiering.open_shift(self.CODE)
		checks = {check["key"]: check for check in audit_checks.precheck(self.CODE, self.today)}
		self.assertEqual(checks[audit_checks.OPEN_SHIFTS]["count"], 1)

		self.as_user("Night Auditor")
		with self.assertRaises(frappe.PermissionError):
			self.start(open_shifts="The cashier went home")
		self.as_user("Front Desk Manager")
		_, status = self.audit(open_shifts="Cashier closes it in the morning")
		self.assertEqual(status, "Completed")

	def test_warnings_are_recorded_but_never_block(self):
		# The attendant finds room 101 empty while the front desk has a guest in it.
		task = housekeeping.create_task(f"{self.CODE}-101", housekeeping.STAYOVER)
		housekeeping.start(task)
		housekeeping.finish(task, "Vacant")

		name, status = self.audit()
		self.assertEqual(status, "Completed")
		self.assertIn("Room discrepancies (1)", self.stage(name, night_audit.PRE_CHECKS).message)
		report = frappe.parse_json(frappe.db.get_value(RUN, name, "audit_report"))
		self.assertEqual([row["check"] for row in report["warnings"]], ["Room discrepancies"])


class TestReconciliation(FullAuditTestCase):
	def drift(self):
		frappe.db.set_value("Guest Folio", self.folio, "balance", flt(self.balance()) + 1)

	def test_a_difference_fails_the_stage_and_a_restart_resumes_from_it(self):
		self.drift()
		name, status = self.audit()
		self.assertEqual(status, "Failed")
		self.assertEqual(self.stage(name, night_audit.POST_ROOM_CHARGES).status, "Completed")
		failed = self.stage(name, night_audit.RECONCILE)
		self.assertEqual(failed.status, "Failed")
		self.assertIn("totals don't match", failed.message)
		self.assertEqual(self.business_date(), self.today)

		# Investigated and fixed: the run resumes at Reconcile and charges nothing twice.
		folio.rebuild_folio_balance(self.folio)
		_, status = self.audit()
		self.assertEqual(status, "Completed")
		self.assertEqual(len(self.night_lines(self.stay.name)), 1)
		self.assertEqual(self.business_date(), self.today + timedelta(days=1))

	def test_a_manager_can_let_the_differences_pass(self):
		self.drift()
		name, _ = self.audit()
		self.as_user("Night Auditor")
		with self.assertRaises(frappe.PermissionError):
			self.start(reconciliation="Accountant will fix it")
		self.as_user("Hospitality Manager")
		_, status = self.audit(reconciliation="Accountant will fix it tomorrow")
		self.assertEqual(status, "Completed")
		self.assertIn("let pass", self.stage(name, night_audit.RECONCILE).message)
		report = frappe.parse_json(frappe.db.get_value(RUN, name, "audit_report"))
		self.assertEqual(len(report["differences"]), 1)

	def test_a_payment_line_reversed_without_a_refund_is_a_difference(self):
		cashiering.open_shift(self.CODE)
		payment = self.pay(1000)
		line = frappe.db.get_value(
			"Folio Payment Allocation", {"folio_payment": payment}, "folio_transaction"
		)
		folio.reverse_transaction(line, "Posted to the wrong folio")
		problems = reconciliation.reversed_payment_lines(self.CODE)
		self.assertEqual([row["name"] for row in problems], [payment])

	def test_the_books_agree_after_a_normal_day(self):
		self.assertEqual(reconciliation.folio_totals(self.CODE), [])
		name, status = self.audit()
		self.assertEqual(status, "Completed")
		self.assertEqual(self.stage(name, night_audit.RECONCILE).status, "Completed")


class TestAuditReport(FullAuditTestCase):
	def test_the_report_keeps_the_days_figures(self):
		cashiering.open_shift(self.CODE)
		self.pay(1000)
		self.settle_with_cash()
		name, status = self.audit()
		self.assertEqual(status, "Completed")
		report = frappe.parse_json(frappe.db.get_value(RUN, name, "audit_report"))
		room = frappe.get_all(
			"Folio Transaction",
			filters={"stay_reservation": self.stay.name, "is_room_revenue": 1},
			fields=["net_amount", "charge_code"],
		)[0]

		rooms = report["rooms"]
		self.assertEqual((rooms["rooms_available"], rooms["rooms_sold"]), (2, 1))
		self.assertEqual(rooms["occupancy"], 50.0)
		self.assertEqual(rooms["room_revenue"], flt(room.net_amount))
		self.assertEqual(rooms["adr"], flt(room.net_amount))
		self.assertEqual(rooms["revpar"], round(flt(room.net_amount) / 2, 2))
		self.assertEqual(rooms["in_house"], 1)
		self.assertEqual({row["charge_code"] for row in report["revenue"]}, {room.charge_code, "TMSG"})
		self.assertEqual([row["amount"] for row in report["payments"]], [1000])
		in_house = next(row for row in report["ledger"] if row["group"] == "In house")
		self.assertEqual(in_house["balance"], flt(self.balance()))


class TestRestartSafety(FullAuditTestCase):
	def test_an_audit_stopped_mid_posting_restarts_without_duplicates(self):
		"""Scenario 36: a run that stopped mid-posting is restarted and completes with no duplicate
		room, package, or levy lines."""
		other = self.second_stay(nights=2)
		check_in(other.name)
		real = night_audit.post_room_night
		calls = {"n": 0}

		def flaky(name, business_date=None):
			calls["n"] += 1
			if calls["n"] == 2:
				raise frappe.ValidationError("worker lost")
			return real(name, business_date)

		with patch.object(night_audit, "post_room_night", side_effect=flaky):
			name, status = self.audit()
		self.assertEqual(status, "Failed")
		self.assertEqual(self.stage(name, night_audit.POST_ROOM_CHARGES).status, "Failed")
		posted_before = self.night_lines(self.stay.name) + self.night_lines(other.name)
		self.assertEqual(len(posted_before), 1)

		_, status = self.audit()
		self.assertEqual(status, "Completed")
		keys = self.night_lines(self.stay.name) + self.night_lines(other.name)
		self.assertEqual(len(keys), 2)
		self.assertEqual(len(keys), len(set(keys)))
		self.assertEqual(self.stage(name, night_audit.RECONCILE).status, "Completed")


class TestCheckOutControls(FullAuditTestCase):
	def test_only_the_balance_can_be_overridden(self):
		"""Scenario 37: incomplete registration or a failed service charge blocks check-out even
		with a manager's override; the override permits only the open balance."""
		primary = frappe.db.get_value(
			"Stay Guest", {"stay_reservation": self.stay.name, "role": "Primary"}, "name"
		)
		self.as_user("Front Desk Manager")
		frappe.db.set_value("Stay Guest", primary, "registration_complete", 0)
		with self.assertRaises(CheckOutBlockedError):
			check_out(self.stay.name, override_reason="Company pays")
		frappe.db.set_value("Stay Guest", primary, "registration_complete", 1)

		failed = frappe.get_doc(
			{
				"doctype": "Service Participant",
				"property": self.prop.name,
				"status": "Failed",
				"role": "Consumer",
				"stay_reservation": self.stay.name,
				"guest_name": "Wanjiku",
				"service_type": None,
				"posting_error": "No charge code",
			}
		)
		failed.name = "HSP-FNA-SVP-1"
		failed.db_insert()
		self.assertEqual([row["kind"] for row in check_out_blockers(self.stay.name)], ["service_charge"])
		with self.assertRaises(CheckOutBlockedError):
			check_out(self.stay.name, override_reason="Company pays")
		frappe.db.set_value("Service Participant", failed.name, "status", "Not Charged")

		# With only the balance left, the manager's override checks the guest out.
		check_out(self.stay.name, override_reason="Company pays on account")
		self.assertEqual(frappe.db.get_value("Stay Reservation", self.stay.name, "status"), "Checked Out")

	def test_a_payment_in_progress_blocks_check_out(self):
		cashiering.open_shift(self.CODE)
		payment = self.phone_payment([{"folio": self.folio, "amount": 4500}])
		blockers = check_out_blockers(self.stay.name)
		self.assertEqual([(row["kind"], row["name"]) for row in blockers], [("payment", payment)])


class TestDryRun(FullAuditTestCase):
	def test_three_business_days_close_without_manual_fixes(self):
		"""An arrival, a stay-over and two departures over three days: every audit completes on its
		own, with no overrides, and the books agree each night."""
		arriving = self.confirmed_stay(nights=1, arrival=self.today + timedelta(days=1))
		runs = []

		# Day 1: the guest in 101 pays for the massage.
		self.settle_with_cash(self.folio)
		runs.append(self.audit())

		# Day 2: the second guest arrives in 102.
		assign_room(arriving.name, f"{self.CODE}-102")
		for guest in frappe.get_all("Stay Guest", filters={"stay_reservation": arriving.name}, pluck="name"):
			register_guest(guest)
		check_in(arriving.name)
		runs.append(self.audit())

		# Day 3: both settle and leave.
		arriving.reload()
		self.settle_with_cash(self.folio, arriving.default_folio)
		check_out(self.stay.name)
		check_out(arriving.name)
		runs.append(self.audit())

		self.assertEqual([status for _, status in runs], ["Completed"] * 3)
		self.assertEqual(self.business_date(), self.today + timedelta(days=3))
		for name, _ in runs:
			self.assertFalse(frappe.get_all("Night Audit Override", filters={"parent": name}))
			self.assertEqual(self.stage(name, night_audit.RECONCILE).status, "Completed")
			self.assertTrue(frappe.db.get_value(RUN, name, "audit_report"))
		self.assertEqual(len(self.night_lines(self.stay.name)), 2)
		self.assertEqual(len(self.night_lines(arriving.name)), 1)


class TestDeskReports(FullAuditTestCase):
	REPORTS = (
		"front_desk_movements",
		"guest_ledger",
		"open_folio_balances",
		"deposits_held",
		"cashier_report",
		"charges_and_adjustments",
		"settlement_pending_folios",
		"occupancy_and_revenue",
	)

	def run_report(self, name, **filters):
		module = frappe.get_module(f"frappoint.vuna_hospitality.report.{name}.{name}")
		return module.execute({"property": self.CODE, **filters})

	def test_every_report_runs_and_occupancy_agrees_with_the_audit(self):
		name, _ = self.audit()
		for report in self.REPORTS:
			columns, data = self.run_report(report)[:2]
			self.assertTrue(columns, report)
		stored = frappe.parse_json(frappe.db.get_value(RUN, name, "audit_report"))["rooms"]
		rows = self.run_report("occupancy_and_revenue", from_date=self.today, to_date=self.today)[1]
		night = rows[0]
		for field in ("rooms_available", "rooms_sold", "occupancy", "room_revenue", "adr", "revpar"):
			self.assertEqual(night[field], stored[field], field)

		in_house = self.run_report("front_desk_movements", list="In House", date=self.today)[1]
		self.assertEqual([row["stay"] for row in in_house], [self.stay.name])
		ledger = self.run_report("guest_ledger")[1]
		self.assertEqual(ledger[-1]["balance"], flt(self.balance()))
