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
