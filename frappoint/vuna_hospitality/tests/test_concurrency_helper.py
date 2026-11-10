import frappe
from frappe.tests import IntegrationTestCase

from frappoint.vuna_hospitality.tests.utils import run_concurrently

LOCK_NAME = "frappoint_hospitality_concurrency_helper_test"


class TestRunConcurrently(IntegrationTestCase):
	def test_functions_run_on_separate_overlapping_connections(self):
		"""Both workers try to take the same named database lock without waiting.

		If they shared a connection, or ran one after the other, both would get it. Running on
		separate connections at the same time, exactly one gets it.
		"""

		def take_lock_and_hold():
			got_it = frappe.db.sql("select get_lock(%s, 0)", LOCK_NAME)[0][0]
			if got_it:
				frappe.db.sql("select sleep(1)")
				frappe.db.sql("select release_lock(%s)", LOCK_NAME)
			return (frappe.db.sql("select connection_id()")[0][0], got_it)

		results = run_concurrently(take_lock_and_hold, take_lock_and_hold, commit=False)

		self.assertTrue(all(result.ok for result in results), [result.error for result in results])
		connection_ids = {result.value[0] for result in results}
		winners = [result for result in results if result.value[1] == 1]
		self.assertEqual(len(connection_ids), 2)
		self.assertEqual(len(winners), 1)

	def test_errors_are_returned_not_raised(self):
		def fail():
			raise frappe.ValidationError("boom")

		results = run_concurrently(fail, lambda: 1, commit=False)

		self.assertIsInstance(results[0].error, frappe.ValidationError)
		self.assertTrue(results[1].ok)
		self.assertEqual(results[1].value, 1)
