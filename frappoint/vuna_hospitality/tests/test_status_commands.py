from unittest import TestCase
from unittest.mock import patch

import frappe

from frappoint.vuna_hospitality.services import status_commands
from frappoint.vuna_hospitality.services.status_commands import (
	InvalidTransitionError,
	allowed_transitions,
	guard_status_change,
	register_transitions,
	transition,
)

DOCTYPE = "Test Hospitality Stay"


class FakeDoc:
	"""Just enough of the Document API for the command framework."""

	doctype = DOCTYPE

	def __init__(self, status, name="STAY-1", new=False):
		self.name = name
		self.values = {"status": status}
		self.saved_status = None if new else status
		self.flags = frappe._dict()
		self.saves = 0
		self._new = new

	def get(self, key):
		return self.values.get(key)

	def set(self, key, value):
		self.values[key] = value

	def update(self, values):
		self.values.update(values)

	def is_new(self):
		return self._new

	def has_value_changed(self, key):
		return self.values.get(key) != self.saved_status

	def save(self, ignore_permissions=False):
		guard_status_change(self)
		self.saves += 1
		self.saved_status = self.values["status"]
		self._new = False


class TestStatusCommands(TestCase):
	@classmethod
	def setUpClass(cls):
		register_transitions(
			DOCTYPE,
			{
				"Held": {"Confirmed", "Expired"},
				"Confirmed": {"In House", "Cancelled"},
				"In House": {"Checked Out"},
				"Cancelled": {"Confirmed"},
			},
			reason_required={("Confirmed", "Cancelled"), ("*", "Confirmed")},
		)

	def setUp(self):
		patcher = patch.object(status_commands, "log_event")
		self.log_event = patcher.start()
		self.addCleanup(patcher.stop)

	def test_allowed_move_saves_and_logs(self):
		doc = FakeDoc("Confirmed")
		result = transition(doc, "In House")

		self.assertEqual(result, {"name": "STAY-1", "from": "Confirmed", "to": "In House", "changed": True})
		self.assertEqual(doc.get("status"), "In House")
		self.assertEqual(doc.saves, 1)
		self.log_event.assert_called_once()
		self.assertEqual(self.log_event.call_args.kwargs["from_status"], "Confirmed")
		self.assertEqual(self.log_event.call_args.kwargs["to_status"], "In House")

	def test_disallowed_move_is_refused_and_not_logged(self):
		doc = FakeDoc("Held")
		with self.assertRaises(InvalidTransitionError):
			transition(doc, "Checked Out")
		self.assertEqual(doc.get("status"), "Held")
		self.log_event.assert_not_called()

	def test_reason_required(self):
		with self.assertRaises(InvalidTransitionError):
			transition(FakeDoc("Confirmed"), "Cancelled", reason="  ")
		transition(FakeDoc("Confirmed"), "Cancelled", reason="Guest called")
		self.assertEqual(self.log_event.call_args.kwargs["reason"], "Guest called")

	def test_wildcard_reason_rule(self):
		with self.assertRaises(InvalidTransitionError):
			transition(FakeDoc("Cancelled"), "Confirmed")
		transition(FakeDoc("Cancelled"), "Confirmed", reason="Reinstated")

	def test_same_status_is_a_noop(self):
		doc = FakeDoc("Held")
		self.assertFalse(transition(doc, "Held")["changed"])
		self.assertEqual(doc.saves, 0)
		self.log_event.assert_not_called()

	def test_updates_are_saved_with_the_transition(self):
		doc = FakeDoc("Confirmed")
		transition(doc, "In House", updates={"checked_in_by": "agent"})
		self.assertEqual(doc.get("checked_in_by"), "agent")

	def test_direct_status_edit_is_refused(self):
		doc = FakeDoc("Confirmed")
		doc.set("status", "Checked Out")
		with self.assertRaises(InvalidTransitionError):
			doc.save()

	def test_other_edits_are_allowed(self):
		doc = FakeDoc("Confirmed")
		doc.set("notes", "late arrival")
		doc.save()
		self.assertEqual(doc.saves, 1)

	def test_new_documents_must_start_in_an_initial_status(self):
		FakeDoc("Held", new=True).save()
		with self.assertRaises(InvalidTransitionError):
			FakeDoc("In House", new=True).save()

	def test_allowed_transitions(self):
		self.assertEqual(allowed_transitions(FakeDoc("Confirmed")), ["Cancelled", "In House"])

	def test_unregistered_doctype(self):
		doc = FakeDoc("Held")
		doc.doctype = "Not Registered"
		with self.assertRaises(InvalidTransitionError):
			transition(doc, "Confirmed")
