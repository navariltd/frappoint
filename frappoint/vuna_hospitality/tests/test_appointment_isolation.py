"""Hospitality must not change how the existing appointment features behave.

Two checks:

1. Every hook that points into the hospitality module either belongs to a hospitality DocType or
   is guarded by the feature flag, so nothing runs for appointment customers who keep it off.
2. The existing appointment test suites pass with hospitality switched on and switched off.
"""

import unittest

import frappe
from frappe.tests import IntegrationTestCase

from frappoint.vuna_hospitality.constants import MODULE
from frappoint.vuna_hospitality.services.feature_flag import GUARD_ATTRIBUTE
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled

HOSPITALITY_PATH = "frappoint.vuna_hospitality."

# Hooks that must run even while hospitality is off, with the reason.
ALLOWED_UNGUARDED_HOOKS = {
	# Hides the hospitality icon, workspace, and dock entry when the module is off.
	"frappoint.vuna_hospitality.doctype.hospitality_settings.hospitality_settings.sync_hospitality_visibility",
	# Property scoping only applies to hospitality DocTypes (see PROPERTY_SCOPED_DOCTYPES).
	"frappoint.vuna_hospitality.services.property_scope.get_permission_query_conditions",
	"frappoint.vuna_hospitality.services.property_scope.has_permission",
}

APPOINTMENT_TEST_MODULES = (
	"frappoint.tests.test_booking_transaction_service",
	"frappoint.tests.test_provider_assignment_service",
	"frappoint.frappoint.services.test_availability_projector",
	"frappoint.frappoint.api.test_booking_desk_couple",
	"frappoint.frappoint.api.test_slot_availability",
)


def _hook_paths(value):
	if isinstance(value, str):
		yield value
	elif isinstance(value, dict):
		for item in value.values():
			yield from _hook_paths(item)
	elif isinstance(value, list | tuple):
		for item in value:
			yield from _hook_paths(item)


class TestAppointmentIsolation(IntegrationTestCase):
	def test_hospitality_hooks_are_guarded(self):
		hospitality_doctypes = set(frappe.get_all("DocType", filters={"module": MODULE}, pluck="name"))
		unguarded = []

		for event_doctype, events in (frappe.get_hooks("doc_events", app_name="frappoint") or {}).items():
			for path in _hook_paths(events):
				if path.startswith(HOSPITALITY_PATH) and event_doctype not in hospitality_doctypes:
					if not getattr(frappe.get_attr(path), GUARD_ATTRIBUTE, False):
						unguarded.append(f"doc_events[{event_doctype}]: {path}")

		for hook in ("scheduler_events", "after_migrate", "on_session_creation", "boot_session"):
			for path in _hook_paths(frappe.get_hooks(hook, app_name="frappoint")):
				if path.startswith(HOSPITALITY_PATH) and path not in ALLOWED_UNGUARDED_HOOKS:
					if not getattr(frappe.get_attr(path), GUARD_ATTRIBUTE, False):
						unguarded.append(f"{hook}: {path}")

		self.assertEqual(unguarded, [], "Wrap these with @hospitality_job or @require_hospitality")

	def test_appointment_suites_pass_with_hospitality_on_and_off(self):
		for state in (False, True):
			with self.subTest(hospitality_enabled=state), hospitality_enabled(state):
				suite = unittest.defaultTestLoader.loadTestsFromNames(APPOINTMENT_TEST_MODULES)
				result = unittest.TestResult()
				suite.run(result)
				failures = [str(test) for test, _ in result.failures + result.errors]
				self.assertTrue(result.testsRun > 0)
				self.assertEqual(failures, [])
