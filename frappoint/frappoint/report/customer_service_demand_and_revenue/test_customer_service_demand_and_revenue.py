import unittest
from unittest.mock import patch

import frappe

from frappoint.frappoint.report.customer_service_demand_and_revenue import (
	customer_service_demand_and_revenue as report,
)


class TestCustomerServiceDemandAndRevenue(unittest.TestCase):
	def setUp(self):
		translation = patch.object(report, "_", side_effect=lambda value: value)
		translation.start()
		self.addCleanup(translation.stop)
		self.filters = dict(company="Test", from_date="2026-01-01", to_date="2026-10-28", currency="KES")

	def test_counts_and_completed_revenue(self):
		appointments = [
			frappe._dict(
				customer=customer,
				full_name="Name",
				appointment_type=service,
				status=status,
				grand_total=amount,
			)
			for customer, service, status, amount in [
				("C1", "Massage", "Completed", "100.10"),
				("C1", "Massage", "Completed", "200.20"),
				("C1", "Massage", "Confirmed", 999),
				("C1", "Facial", "Completed", 50),
				("C2", "Massage", "Open", None),
			]
		]
		with patch.object(frappe, "get_list", return_value=appointments):
			columns, rows, message, chart = report.execute(self.filters)
		self.assertEqual(len(columns), 8)
		self.assertEqual(len(rows), 5)
		self.assertTrue(rows[0]["is_customer_total"])
		self.assertEqual(rows[0]["appointments_requested"], 4)
		self.assertEqual(rows[0]["completed_appointments"], 3)
		self.assertEqual(rows[0]["revenue"], 350.30)
		self.assertEqual(rows[1]["appointments_requested"], 3)
		self.assertEqual(rows[1]["revenue"], 300.30)
		self.assertEqual(rows[1]["parent_customer"], "C1")
		self.assertEqual(rows[1]["indent"], 1)
		self.assertEqual(rows[3]["customer"], "C2")
		self.assertTrue(rows[3]["is_customer_total"])
		self.assertEqual(rows[4]["revenue"], 0)
		self.assertEqual(chart["data"]["labels"], ["C1"])
		self.assertEqual(chart["data"]["datasets"][0]["values"], [350.30])
		# Framework totals must sum parent rows only, avoiding duplicate service totals.
		parents = [row for row in rows if not row.get("parent_customer")]
		self.assertEqual(sum(row["appointments_requested"] for row in parents), 5)
		self.assertEqual(sum(row["completed_appointments"] for row in parents), 3)
		self.assertEqual(sum(row["revenue"] for row in parents), 350.30)

	def test_filters_empty_results_and_currency_default(self):
		filters = {
			**self.filters,
			"currency": None,
			"customer": "C1",
			"service_type": "Massage",
			"status": "Completed",
		}
		with (
			patch.object(frappe, "get_cached_value", return_value="KES"),
			patch.object(frappe, "get_list", return_value=[]) as query,
		):
			result = report.execute(filters)
		self.assertEqual(result[1], [])
		self.assertIsNone(result[3])
		conditions = query.call_args.kwargs["filters"]
		for field, value in dict(
			company="Test", currency="KES", customer="C1", appointment_type="Massage", status="Completed"
		).items():
			self.assertEqual(conditions[field], value)
		self.assertEqual(conditions["docstatus"], ["<", 2])
		self.assertEqual(query.call_args.kwargs["limit_page_length"], 0)
		with patch.object(frappe, "get_list", return_value=[]) as query:
			report.execute(self.filters)
		self.assertEqual(query.call_args.kwargs["filters"]["status"], ["!=", "Cancelled"])

	def test_chart_top_ten_and_others(self):
		rows = [dict(customer=f"C{i:02}", revenue=i) for i in range(1, 13)]
		chart = report.get_chart(rows, "KES")
		self.assertEqual(len(chart["data"]["labels"]), 11)
		self.assertEqual(chart["data"]["labels"][-1], "Others")
		self.assertEqual(chart["data"]["datasets"][0]["values"][-1], 3)
		self.assertIsNone(report.get_chart([dict(customer="C1", revenue=0)], "KES"))
		self.assertIsNone(report.get_chart([dict(customer="C1", revenue=-1)], "KES"))

	def test_invalid_filters(self):
		with patch.object(frappe, "throw", side_effect=ValueError), patch.object(frappe, "get_list") as query:
			for overrides in (
				{"company": None},
				{"from_date": None},
				{"to_date": None},
				{"from_date": "2027-01-01"},
				{"status": "Cancelled"},
			):
				with self.subTest(overrides=overrides), self.assertRaises(ValueError):
					report.execute({**self.filters, **overrides})
			query.assert_not_called()
