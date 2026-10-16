# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import patch

import frappe

from frappoint.frappoint.report.service_provider_performance import service_provider_performance as report


class TestServiceProviderPerformance(unittest.TestCase):
	def setUp(self):
		translation = patch.object(report, "_", side_effect=lambda value: value)
		translation.start()
		self.addCleanup(translation.stop)
		self.filters = {"from_date": "2026-01-01", "to_date": "2026-10-14"}

	def test_counts_revenue_and_separate_currencies(self):
		appointments = [
			frappe._dict(
				appointment_provider=provider,
				service_provider_name=name,
				status="Completed",
				currency=currency,
				grand_total=amount,
			)
			for provider, name, currency, amount in [
				("P1", "Alice", "KES", "100.10"),
				("P1", "Alice", "KES", "200.20"),
				("P1", "Alice", "USD", 20),
				("P2", "Bob", "KES", 0),
				("P2", "Bob", "KES", None),
			]
		]
		with patch.object(frappe, "get_list", return_value=appointments):
			columns, rows = report.execute(self.filters)
		self.assertEqual(len(columns), 6)
		self.assertEqual(len(rows), 3)
		self.assertEqual(rows[0]["completed_appointments"], 2)
		self.assertEqual(rows[0]["total_revenue"], 300.30)
		self.assertEqual(rows[0]["provider_name"], "Alice")
		self.assertEqual(rows[1]["total_revenue"], 20)
		self.assertEqual(rows[2]["completed_appointments"], 2)
		self.assertEqual(rows[2]["total_revenue"], 0)

	def test_confirmed_appointments_include_providers_without_completions(self):
		appointments = [
			frappe._dict(
				appointment_provider=provider,
				service_provider_name=provider,
				status=status,
				currency=currency,
				grand_total=amount,
			)
			for provider, status, currency, amount in [
				("P1", "Completed", "KES", 100),
				("P1", "Confirmed", "KES", 200),
				("P1", "Confirmed", "KES", 300),
				("P1", "Confirmed", "USD", 20),
				("P2", "Confirmed", "KES", 400),
			]
		]
		with patch.object(frappe, "get_list", return_value=appointments):
			columns, rows = report.execute(self.filters)
		self.assertIn("confirmed_appointments", [column["fieldname"] for column in columns])
		self.assertEqual([row["confirmed_appointments"] for row in rows], [2, 1, 1])
		self.assertEqual([row["completed_appointments"] for row in rows], [1, 0, 0])
		self.assertEqual([row["total_revenue"] for row in rows], [100, 0, 0])

	def test_query_filters_and_empty_results(self):
		for provider in (None, "P1"):
			with self.subTest(provider=provider):
				filters = {**self.filters, "company": "Test Company", "service_provider": provider}
				with patch.object(frappe, "get_list", return_value=[]) as query:
					self.assertEqual(report.execute(filters)[1], [])
				conditions = query.call_args.kwargs["filters"]
				self.assertEqual(conditions["company"], "Test Company")
				self.assertEqual(conditions["appointment_provider"], provider or ["is", "set"])
				self.assertEqual(conditions["status"], ["in", ["Confirmed", "Completed"]])
				self.assertEqual(conditions["docstatus"], ["<", 2])
				self.assertEqual(
					[str(d) for d in conditions["appointment_date"][1]], ["2026-01-01", "2026-10-14"]
				)
				self.assertEqual(query.call_args.kwargs["limit_page_length"], 0)

	def test_optional_filters(self):
		with patch.object(frappe, "get_list", return_value=[]) as query:
			report.execute(self.filters)
		self.assertNotIn("company", query.call_args.kwargs["filters"])

	def test_invalid_dates(self):
		with patch.object(frappe, "throw", side_effect=ValueError):
			for overrides in ({"from_date": None}, {"to_date": None}, {"from_date": "2026-12-01"}):
				with self.subTest(overrides=overrides), self.assertRaises(ValueError):
					report.execute({**self.filters, **overrides})
