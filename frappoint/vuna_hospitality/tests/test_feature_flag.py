import frappe
from frappe.tests import IntegrationTestCase

from frappoint.vuna_hospitality.api.session import get_session_context
from frappoint.vuna_hospitality.services.feature_flag import (
	HospitalityDisabledError,
	hospitality_job,
	is_hospitality_enabled,
	require_hospitality,
)
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled


@require_hospitality
def _api_action(value):
	return value * 2


class _RefusedError(frappe.ValidationError):
	pass


@require_hospitality
def _refuse(explained=False):
	if explained:
		frappe.throw("Already explained.", _RefusedError)
	raise _RefusedError("Register every adult before check-in: Grace Wanjiru.")


@hospitality_job
def _job(value):
	return value * 3


class TestFeatureFlag(IntegrationTestCase):
	def test_flag_helper_switches_state(self):
		with hospitality_enabled(True):
			self.assertTrue(is_hospitality_enabled())
		with hospitality_enabled(False):
			self.assertFalse(is_hospitality_enabled())

	def test_api_guard_refuses_when_disabled(self):
		with hospitality_enabled(False), self.assertRaises(HospitalityDisabledError):
			_api_action(2)

	def test_api_guard_runs_when_enabled(self):
		with hospitality_enabled(True):
			self.assertEqual(_api_action(2), 4)

	def test_job_guard_skips_quietly_when_disabled(self):
		with hospitality_enabled(False):
			self.assertIsNone(_job(2))
		with hospitality_enabled(True):
			self.assertEqual(_job(2), 6)

	def test_session_context_reports_state_instead_of_raising(self):
		with hospitality_enabled(False):
			self.assertFalse(get_session_context()["enabled"])
		with hospitality_enabled(True):
			context = get_session_context()
		self.assertTrue(context["enabled"])
		self.assertEqual(context["user"], "Administrator")
		self.assertIsNone(context["properties"])

	def test_a_typed_refusal_reaches_the_desk_as_a_message(self):
		"""Raised without frappe.throw, Frappe would send only the type ("Server Error")."""
		frappe.clear_messages()
		with hospitality_enabled(True), self.assertRaises(_RefusedError):
			_refuse()
		self.assertEqual(
			[
				frappe.parse_json(row).get("message") if isinstance(row, str) else row.get("message")
				for row in frappe.local.message_log
			],
			["Register every adult before check-in: Grace Wanjiru."],
		)

		frappe.clear_messages()
		with hospitality_enabled(True), self.assertRaises(_RefusedError):
			_refuse(explained=True)
		self.assertEqual(len(frappe.local.message_log), 1)  # not added twice
