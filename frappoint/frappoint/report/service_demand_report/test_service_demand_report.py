# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import frappe
from pypika import Table

from frappoint.frappoint.report.service_demand_report import service_demand_report as report


class TestServiceDemandReport(unittest.TestCase):
	def setUp(self):
		translation = patch.object(report, "_", side_effect=lambda value: value)
		translation.start()
		self.addCleanup(translation.stop)
		qb_patch = patch.object(frappe, "qb", MagicMock())
		self.qb = qb_patch.start()
		self.addCleanup(qb_patch.stop)
		self.qb.DocType.return_value = Table("tabService Appointment")
		self.query = self.qb.get_query.return_value
		self.query.where.return_value = self.query
		self.query.run.return_value = []

	def test_week_is_monday_to_sunday_with_daily_counts(self):
		columns, rows = report.execute({"week_start": "2026-10-18"})
		self.assertEqual(rows, [])
		self.assertEqual(len(columns), 9)
		self.assertEqual(columns[1]["label"], "Monday (12 Oct)")
		self.assertEqual(columns[7]["label"], "Sunday (18 Oct)")
		kwargs = self.qb.get_query.call_args.kwargs
		self.assertEqual(kwargs["filters"]["appointment_date"], ["between", [date(2026, 10, 12), date(2026, 10, 18)]])
		self.assertFalse(kwargs["ignore_permissions"])
		self.assertEqual(kwargs["group_by"], "appointment_type")
		self.assertEqual(kwargs["filters"]["docstatus"], ["<", 2])
		self.assertEqual(kwargs["filters"]["status"], ["!=", "Cancelled"])
		fields = kwargs["fields"]
		self.assertIn("SUM(CASE WHEN", str(fields[1]))
		self.assertIn("2026-10-12", str(fields[1]))
		self.assertIn("2026-10-18", str(fields[7]))
		self.assertIn("COUNT(", str(fields[8]))
		criterion = str(self.query.where.call_args.args[0])
		self.assertIn("'Confirmed','Completed'", criterion)
		self.assertIn("OR", criterion)
		self.assertIn("'Paid'", criterion)
		self.query.run.assert_called_once_with(as_dict=True)

	def test_filters_and_aggregated_results(self):
		rows = [{"service_type": "Massage", "monday": 2, "weekly_total": 2}]
		self.query.run.return_value = rows
		self.assertEqual(report.execute({"week_start": "2026-01-01", "company": "Test", "service_type": "Massage"})[1], rows)
		conditions = self.qb.get_query.call_args.kwargs["filters"]
		self.assertEqual(conditions["company"], "Test")
		self.assertEqual(conditions["appointment_type"], "Massage")
		self.assertEqual(conditions["appointment_date"][1], [date(2025, 12, 29), date(2026, 1, 4)])

	def test_week_is_required(self):
		with patch.object(frappe, "throw", side_effect=ValueError):
			with self.assertRaises(ValueError):
				report.execute()
		self.qb.get_query.assert_not_called()
