from datetime import date, time
from unittest import TestCase
from unittest.mock import patch

from frappoint.frappoint.api import slot_availability


def _couple_candidate():
	return {
		"candidate_id": "candidate-1",
		"is_couple": 1,
		"date": date(2026, 8, 10),
		"start_time": time(9, 0),
		"end_time": time(10, 0),
		"end_time_1": time(9, 45),
		"end_time_2": time(10, 0),
		"provider_1": "PROVIDER-1",
		"provider_name_1": "Provider One",
		"provider_2": "PROVIDER-2",
		"provider_name_2": "Provider Two",
		"guest_1": {
			"service_type": "SERVICE-1",
			"provider": "PROVIDER-1",
			"provider_name": "Provider One",
			"date": date(2026, 8, 10),
			"start_time": time(9, 0),
			"end_time": time(9, 45),
			"duration": 45,
			"buffer_before": 10,
			"buffer_after": 5,
			"slot_ids": [],
		},
		"guest_2": {
			"service_type": "SERVICE-2",
			"provider": "PROVIDER-2",
			"provider_name": "Provider Two",
			"date": date(2026, 8, 10),
			"start_time": time(9, 0),
			"end_time": time(10, 0),
			"duration": 60,
			"buffer_before": 0,
			"buffer_after": 15,
			"slot_ids": [],
		},
	}


class TestCoupleSlotAvailabilityApi(TestCase):
	@patch.object(slot_availability, "_filter_couple_provider_gender", side_effect=lambda rows, *_: rows)
	@patch.object(
		slot_availability,
		"_filter_couple_all_day_provider_unavailability",
		side_effect=lambda rows: rows,
	)
	@patch.object(slot_availability, "get_projected_couple_available_slots")
	def test_existing_time_endpoint_accepts_couple_parameter_names(
		self,
		projected_slots,
		_filter_unavailability,
		_filter_gender,
	):
		projected_slots.return_value = [_couple_candidate()]

		result = slot_availability.get_available_time_slots(
			service_type_1="SERVICE-1",
			service_type_2="SERVICE-2",
			duration_1=45,
			duration_2=60,
			provider_1="PROVIDER-1",
			provider_2="PROVIDER-2",
			exclude_appointment_id_1="APT-1",
			exclude_appointment_id_2="APT-2",
			start_date="2026-08-10",
			end_date="2026-08-12",
		)

		projected_slots.assert_called_once_with(
			service_type_1="SERVICE-1",
			service_type_2="SERVICE-2",
			start_date=date(2026, 8, 10),
			end_date=date(2026, 8, 12),
			provider_1="PROVIDER-1",
			provider_2="PROVIDER-2",
			service_unit_1=None,
			service_unit_2=None,
			duration_1=45,
			duration_2=60,
			exclude_appointment_id_1="APT-1",
			exclude_appointment_id_2="APT-2",
		)
		self.assertEqual(result[0]["date"], "2026-08-10")
		self.assertEqual(result[0]["slots"][0]["guest_1"]["end_time"], "09:45:00")
		self.assertEqual(result[0]["slots"][0]["guest_2"]["end_time"], "10:00:00")

	@patch.object(slot_availability, "format_available_slots")
	@patch.object(slot_availability, "get_projected_available_slots")
	def test_single_service_endpoint_keeps_legacy_projection_shape(self, projected_slots, formatter):
		rows = [
			{
				"provider": "PROVIDER-1",
				"date": date(2026, 8, 10),
				"start_time": time(9, 0),
				"end_time": time(9, 30),
			}
		]
		projected_slots.return_value = rows
		formatter.return_value = [{"date": "2026-08-10", "slots": []}]

		result = slot_availability.get_available_time_slots(
			service_type="SERVICE-1",
			duration=30,
			provider="PROVIDER-1",
			date="2026-08-10",
		)

		projected_slots.assert_called_once_with(
			service_type_id="SERVICE-1",
			start_date=date(2026, 8, 10),
			end_date=date(2026, 8, 10),
			provider_id="PROVIDER-1",
			required_duration_minutes=30,
		)
		formatter.assert_called_once_with(rows)
		self.assertEqual(result, formatter.return_value)
