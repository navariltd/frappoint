from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from frappoint.frappoint.services.provider_assignment_service import select_provider_for_assignment


class TestProviderAssignmentService(FrappeTestCase):
	def test_selects_less_loaded_provider_before_alphabetical_order(self):
		options = [
			{"provider": "Alice", "provider_name": "Alice"},
			{"provider": "Jane", "provider_name": "Jane"},
			{"provider": "Peter", "provider_name": "Peter"},
		]
		metadata = {
			"Alice": {"provider_name": "Alice", "gender": "Female"},
			"Jane": {"provider_name": "Jane", "gender": "Female"},
			"Peter": {"provider_name": "Peter", "gender": "Male"},
		}
		loads = {
			"Alice": {
				"day_count": 0,
				"service_window_count": 1,
				"overall_window_count": 1,
				"last_assigned_at": "2026-06-01 09:00:00",
			},
			"Jane": {
				"day_count": 0,
				"service_window_count": 0,
				"overall_window_count": 0,
				"last_assigned_at": None,
			},
			"Peter": {
				"day_count": 0,
				"service_window_count": 0,
				"overall_window_count": 0,
				"last_assigned_at": None,
			},
		}

		with (
			patch(
				"frappoint.frappoint.services.provider_assignment_service._get_provider_metadata",
				return_value=metadata,
			),
			patch(
				"frappoint.frappoint.services.provider_assignment_service._get_provider_load_metrics",
				return_value=loads,
			),
		):
			selected = select_provider_for_assignment(
				options,
				appointment_date="2026-06-10",
				service_type="Massage",
			)

		self.assertEqual(selected["provider"], "Jane")

	def test_respects_preferred_gender_before_fairness_ranking(self):
		options = [
			{"provider": "Alice", "provider_name": "Alice"},
			{"provider": "Peter", "provider_name": "Peter"},
		]
		metadata = {
			"Alice": {"provider_name": "Alice", "gender": "Female"},
			"Peter": {"provider_name": "Peter", "gender": "Male"},
		}
		loads = {
			"Alice": {
				"day_count": 0,
				"service_window_count": 0,
				"overall_window_count": 0,
				"last_assigned_at": None,
			},
			"Peter": {
				"day_count": 10,
				"service_window_count": 10,
				"overall_window_count": 10,
				"last_assigned_at": "2026-06-01 09:00:00",
			},
		}

		with (
			patch(
				"frappoint.frappoint.services.provider_assignment_service._get_provider_metadata",
				return_value=metadata,
			),
			patch(
				"frappoint.frappoint.services.provider_assignment_service._get_provider_load_metrics",
				return_value=loads,
			),
		):
			selected = select_provider_for_assignment(
				options,
				appointment_date="2026-06-10",
				service_type="Massage",
				preferred_gender="Male",
			)

		self.assertEqual(selected["provider"], "Peter")
