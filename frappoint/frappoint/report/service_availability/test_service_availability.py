# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import unittest
from datetime import date, time
from unittest.mock import patch

import frappe

from frappoint.frappoint.report.service_availability import service_availability as report

FILTERS = {"service_type": "Massage", "duration": 60, "date_from": "2026-11-16", "date_to": "2026-11-17"}


def _slot(day, start, end, provider, provider_name, unit=None, unit_name=None):
	return {
		"date": day,
		"start_time": start,
		"end_time": end,
		"duration": 60,
		"provider": provider,
		"provider_name": provider_name,
		"service_unit": unit,
		"service_unit_name": unit_name,
	}


SLOTS = [
	_slot(date(2026, 11, 16), time(9), time(10), "P1", "Alice", "U1", "Room 1"),
	_slot(date(2026, 11, 16), time(9), time(10), "P2", "Bob", "U2", "Room 2"),
	_slot(date(2026, 11, 16), time(14), time(15), "P1", "Alice", "U1", "Room 1"),
	_slot(date(2026, 11, 17), time(11), time(12), "P2", "Bob", "U2", "Room 2"),
]


class TestServiceAvailability(unittest.TestCase):
	def setUp(self):
		for target, kwargs in (
			("_", {"side_effect": lambda value: value}),
			("get_projected_available_slots", {"return_value": list(SLOTS)}),
		):
			patcher = patch.object(report, target, **kwargs)
			patcher.start()
			self.addCleanup(patcher.stop)

		# Answer only the doctypes the report queries. Patching frappe.get_all wholesale also hijacks
		# Frappe internals (e.g. formatdate loading the Language doc), so pass everything else through.
		self.get_all_results = {
			"Service Unit": [frappe._dict(name="U1", capacity=1), frappe._dict(name="U2", capacity=2)],
		}
		real_get_all = frappe.get_all

		def fake_get_all(doctype, *args, **kwargs):
			if doctype in self.get_all_results:
				return self.get_all_results[doctype]
			return real_get_all(doctype, *args, **kwargs)

		get_all = patch.object(report.frappe, "get_all", side_effect=fake_get_all)
		self.get_all = get_all.start()
		self.addCleanup(get_all.stop)

	def _run(self, **extra):
		_columns, data = report.execute({**FILTERS, **extra})
		return data

	def test_rows_are_grouped_date_then_start_time_then_option(self):
		data = self._run()

		self.assertEqual(
			[(row["indent"], row["label"].split(",")[0]) for row in data],
			[
				(0, "Mon"),
				(1, "09:00"),
				(2, "Alice · Room 1"),
				(2, "Bob · Room 2"),
				(1, "14:00"),
				(2, "Alice · Room 1"),
				(0, "Tue"),
				(1, "11:00"),
				(2, "Bob · Room 2"),
			],
		)

	def test_children_point_at_their_parent(self):
		data = self._run()
		keys = {row["key"] for row in data}

		for row in data:
			if row["indent"] == 0:
				self.assertIsNone(row["parent_key"])
			else:
				self.assertIn(row["parent_key"], keys)

	def test_group_rows_summarise_their_options(self):
		data = self._run()
		monday, nine_am = data[0], data[1]

		self.assertEqual(monday["available_options"], 3)
		self.assertEqual(monday["provider_count"], 2)
		self.assertEqual(monday["start_time"], time(9))
		self.assertEqual(monday["end_time"], time(15))
		self.assertEqual(nine_am["available_options"], 2)
		self.assertEqual(nine_am["providers"], "Alice, Bob")
		self.assertEqual(nine_am["service_units"], "Room 1, Room 2")
		self.assertEqual(nine_am["service_unit_capacity"], 3)

	def test_start_time_from_and_to(self):
		data = self._run(start_time_from="10:00:00", start_time_to="13:00:00")
		self.assertEqual([row["label"] for row in data if row["indent"] == 1], ["11:00"])

		data = self._run(start_time_from="12:00:00")
		self.assertEqual([row["label"] for row in data if row["indent"] == 1], ["14:00"])

		data = self._run(start_time_to="09:00:00")
		self.assertEqual([row["label"] for row in data if row["indent"] == 1], ["09:00"])

	def test_start_time_range_must_be_in_order(self):
		with self.assertRaises(frappe.ValidationError):
			self._run(start_time_from="15:00:00", start_time_to="09:00:00")

	def test_gender_filter(self):
		self.get_all_results["Service Provider"] = ["P2"]
		data = self._run(gender="Male")
		providers = {row["provider"] for row in data if row["indent"] == 2}
		self.assertEqual(providers, {"P2"})
		self.get_all.assert_any_call("Service Provider", filters={"gender": "Male"}, pluck="name")

	def test_required_filters_missing_returns_nothing(self):
		_columns, data = report.execute({"service_type": "Massage"})
		self.assertEqual(data, [])
