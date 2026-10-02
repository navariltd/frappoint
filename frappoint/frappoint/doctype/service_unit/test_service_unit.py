# Copyright (c) 2025, Navari LTD and Contributors
# See license.txt

from datetime import date
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from frappoint.frappoint.doctype.service_unit import service_unit


class TestServiceUnit(TestCase):
	def test_availability_setting_changes_refresh_unit_booking_horizon(self):
		for field in ("capacity", "allow_overlap", "allow_appointments", "disabled"):
			with self.subTest(field=field):
				unit = Mock(name="unit")
				unit.name = "Maisha"
				unit.get_doc_before_save.return_value = object()
				unit.has_value_changed.side_effect = lambda candidate: candidate == field
				with (
					patch.object(
						service_unit.frappe, "get_cached_doc", return_value=frappe._dict(max_advance_days=30)
					),
					patch.object(service_unit, "nowdate", return_value="2026-10-02"),
					patch.object(service_unit, "enqueue_targeted_counter_refresh") as refresh,
				):
					service_unit.ServiceUnit.on_update(unit)
				refresh.assert_called_once_with(
					start_date=date(2026, 10, 1),
					end_date=date(2026, 11, 1),
					service_unit="Maisha",
				)

	def test_unrelated_changes_and_new_units_do_not_refresh_counters(self):
		for previous in (None, object()):
			with self.subTest(previous=previous):
				unit = Mock()
				unit.get_doc_before_save.return_value = previous
				unit.has_value_changed.return_value = False
				with patch.object(service_unit, "enqueue_targeted_counter_refresh") as refresh:
					service_unit.ServiceUnit.on_update(unit)
				refresh.assert_not_called()
