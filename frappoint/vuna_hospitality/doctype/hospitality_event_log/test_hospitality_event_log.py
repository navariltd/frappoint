# Copyright (c) 2026, Navari LTD and Contributors
# See license.txt

import json

import frappe
from frappe.tests import IntegrationTestCase

from frappoint.vuna_hospitality.services.event_log import log_event

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["User"]


class IntegrationTestHospitalityEventLog(IntegrationTestCase):
	def _entry(self):
		return log_event(
			"Hospitality Settings",
			"Hospitality Settings",
			"Settings Changed",
			from_status="Off",
			to_status="On",
			reason="Pilot go-live",
			data={"enable_hospitality": [0, 1]},
		)

	def test_log_event_records_actor_and_context(self):
		entry = self._entry()

		self.assertTrue(entry.name.startswith("HSP-LOG-"))
		self.assertEqual(entry.reference_doctype, "Hospitality Settings")
		self.assertEqual(entry.event_type, "Settings Changed")
		self.assertEqual(entry.user, "Administrator")
		self.assertIsNotNone(entry.timestamp)
		self.assertIsNone(entry.property)  # a single DocType has no property
		self.assertEqual(json.loads(entry.data), {"enable_hospitality": [0, 1]})

	def test_entries_cannot_be_edited(self):
		entry = frappe.get_doc("Hospitality Event Log", self._entry().name)
		entry.reason = "changed"
		with self.assertRaises(frappe.PermissionError):
			entry.save(ignore_permissions=True)

	def test_entries_cannot_be_deleted(self):
		name = self._entry().name
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Hospitality Event Log", name, ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Hospitality Event Log", name))
