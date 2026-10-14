# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import patch

import frappe

from frappoint.frappoint.report.treatment_revenue_analytics import treatment_revenue_analytics as report


class TestTreatmentRevenueAnalytics(unittest.TestCase):
	def setUp(self):
		translation = patch.object(report, "_", side_effect=lambda value: value)
		translation.start()
		self.addCleanup(translation.stop)

	def filters(self, **overrides):
		filters = frappe._dict(from_date="2025-01-15", to_date="2025-03-10", range="Monthly")
		filters.update(overrides)
		report.validate_filters(filters)
		return filters

	def test_partial_months_and_quarters(self):
		periods = report.get_periods(self.filters())
		self.assertEqual([p["label"] for p in periods], ["Jan 2025", "Feb 2025", "Mar 2025"])
		periods = report.get_periods(self.filters(range="Quarterly", to_date="2025-04-01"))
		self.assertEqual([p["label"] for p in periods], ["Quarter 1 2025", "Quarter 2 2025"])

	def test_week_and_year_boundaries(self):
		periods = report.get_periods(self.filters(range="Weekly", from_date="2024-12-30", to_date="2025-01-06"))
		self.assertEqual([p["label"] for p in periods], ["Week 1 2025", "Week 2 2025"])
		periods = report.get_periods(self.filters(range="Yearly", from_date="2023-06-01", to_date="2026-01-01"))
		self.assertEqual([p["label"] for p in periods], ["2023", "2024", "2025", "2026"])

	def test_revenue_averages_zero_periods_and_currency_separation(self):
		appointments = [
			frappe._dict(appointment_type="Massage", appointment_date=date, currency=currency, grand_total=amount)
			for date, currency, amount in [
				("2025-01-20", "KES", 100), ("2025-01-21", "KES", 200),
				("2025-03-01", "KES", 600), ("2025-01-20", "USD", 20),
			]
		]
		with patch.object(frappe, "get_list", return_value=appointments) as query:
			columns, rows = report.execute(self.filters(company="Test Company"))
		self.assertEqual(rows[0]["completed_appointments"], 3)
		self.assertEqual(rows[0]["total_revenue"], 900)
		self.assertEqual(rows[0]["average_revenue"], 300)
		self.assertEqual(rows[0]["period_20250101_average_revenue"], 150)
		self.assertEqual(rows[0]["period_20250201_average_revenue"], 0)
		self.assertEqual(rows[1]["total_revenue"], 20)
		self.assertEqual(len(columns), 14)
		conditions = query.call_args.kwargs["filters"]
		self.assertEqual(conditions["status"], "Completed")
		self.assertEqual(conditions["docstatus"], ["<", 2])
		self.assertEqual(conditions["company"], "Test Company")
		self.assertEqual(str(conditions["appointment_date"][1][0]), "2025-01-15")

	def test_empty_results(self):
		with patch.object(frappe, "get_list", return_value=[]):
			self.assertEqual(report.execute(self.filters())[1], [])

	def test_invalid_filters(self):
		with patch.object(frappe, "throw", side_effect=ValueError):
			for overrides in ({"from_date": None}, {"to_date": None}, {"from_date": "2026-01-01"}, {"range": "Daily"}):
				with self.subTest(overrides=overrides), self.assertRaises(ValueError):
					self.filters(**overrides)
