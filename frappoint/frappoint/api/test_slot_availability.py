from copy import deepcopy
from datetime import date, time
from unittest import TestCase
from unittest.mock import Mock, patch

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
	@patch.object(slot_availability, "_build_couple_candidate_filter")
	@patch.object(slot_availability, "get_projected_couple_available_slots")
	def test_existing_time_endpoint_accepts_couple_parameter_names(
		self,
		projected_slots,
		candidate_filter_builder,
	):
		provider_z = _couple_candidate()
		provider_z["candidate_id"] = "candidate-z"
		provider_z["provider_1"] = "PROVIDER-Z"
		provider_z["provider_name_1"] = "Provider Z"
		provider_z["guest_1"]["provider"] = "PROVIDER-Z"
		provider_z["guest_1"]["provider_name"] = "Provider Z"

		provider_a = deepcopy(provider_z)
		provider_a["candidate_id"] = "candidate-a"
		provider_a["provider_1"] = "PROVIDER-A"
		provider_a["provider_name_1"] = "Provider A"
		provider_a["guest_1"]["provider"] = "PROVIDER-A"
		provider_a["guest_1"]["provider_name"] = "Provider A"

		later = deepcopy(provider_a)
		later["candidate_id"] = "candidate-later"
		later["start_time"] = time(10, 0)
		later["guest_1"]["start_time"] = time(10, 0)
		later["guest_2"]["start_time"] = time(10, 0)

		projected_slots.return_value = [provider_z, later, provider_a]

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
			end_date="2026-08-10",
		)

		projected_slots.assert_called_once_with(
			service_type_1="SERVICE-1",
			service_type_2="SERVICE-2",
			start_date=date(2026, 8, 10),
			end_date=date(2026, 8, 10),
			provider_1="PROVIDER-1",
			provider_2="PROVIDER-2",
			service_unit_1=None,
			service_unit_2=None,
			duration_1=45,
			duration_2=60,
			exclude_appointment_id_1="APT-1",
			exclude_appointment_id_2="APT-2",
			candidate_filter=candidate_filter_builder.return_value,
			max_candidates_per_start=1,
		)
		self.assertEqual(result[0]["date"], "2026-08-10")
		self.assertEqual(
			[row["candidate_id"] for row in result[0]["slots"]],
			["candidate-a", "candidate-later"],
		)
		self.assertEqual(result[0]["slots"][0]["guest_1"]["end_time"], "09:45:00")
		self.assertEqual(result[0]["slots"][0]["guest_2"]["end_time"], "10:00:00")

	@patch.object(
		slot_availability,
		"_clamp_couple_date_discovery_range",
		side_effect=lambda start, end: (start, end),
	)
	@patch.object(slot_availability, "_build_couple_candidate_filter")
	@patch.object(slot_availability, "get_projected_couple_available_slots")
	def test_date_endpoint_stops_after_one_eligible_candidate_per_date(
		self,
		projected_slots,
		candidate_filter_builder,
		_clamp_range,
	):
		projected_slots.return_value = [_couple_candidate()]

		result = slot_availability.get_couple_available_dates(
			service_type_1="SERVICE-1",
			service_type_2="SERVICE-2",
			duration_1=45,
			duration_2=60,
			gender_1="Female",
			gender_2="Male",
			start_date="2026-08-10",
			end_date="2026-08-12",
		)

		candidate_filter_builder.assert_called_once_with(
			start_date=date(2026, 8, 10),
			end_date=date(2026, 8, 12),
			gender_1="Female",
			gender_2="Male",
		)
		_clamp_range.assert_called_once_with(date(2026, 8, 10), date(2026, 8, 12))
		self.assertEqual(projected_slots.call_args.kwargs["max_candidates_per_date"], 1)
		self.assertIs(
			projected_slots.call_args.kwargs["candidate_filter"],
			candidate_filter_builder.return_value,
		)
		self.assertEqual(result, ["2026-08-10"])

	def test_candidate_filter_applies_gender_and_all_day_unavailability_before_limits(self):
		def get_all(doctype, *, filters, **_kwargs):
			if doctype == "Service Provider":
				return {
					"Female": ["PROVIDER-1"],
					"Male": ["PROVIDER-2", "PROVIDER-BLOCKED"],
				}[filters["gender"]]
			return [
				{
					"provider": "PROVIDER-BLOCKED",
					"from_date": date(2026, 8, 10),
					"to_date": date(2026, 8, 11),
				}
			]

		with (
			patch.object(slot_availability.frappe, "get_all", side_effect=get_all),
			patch.dict(
				slot_availability.frappe.__dict__,
				{"db": Mock(table_exists=Mock(return_value=True))},
			),
		):
			candidate_filter = slot_availability._build_couple_candidate_filter(
				start_date="2026-08-10",
				end_date="2026-08-12",
				gender_1="Female",
				gender_2="Male",
			)

		wrong_gender = _couple_candidate()
		wrong_gender["guest_1"]["provider"] = "PROVIDER-OTHER"
		blocked = _couple_candidate()
		blocked["guest_2"]["provider"] = "PROVIDER-BLOCKED"
		eligible = _couple_candidate()

		self.assertFalse(candidate_filter(wrong_gender))
		self.assertFalse(candidate_filter(blocked))
		self.assertTrue(candidate_filter(eligible))

	def test_candidate_limit_defaults_to_one_and_is_capped(self):
		self.assertEqual(slot_availability._resolve_couple_candidate_limit(None), 1)
		self.assertEqual(slot_availability._resolve_couple_candidate_limit("4"), 4)
		self.assertEqual(slot_availability._resolve_couple_candidate_limit(100), 10)

	def test_date_discovery_range_is_clamped_to_the_configured_horizon(self):
		with patch.dict(
			slot_availability.frappe.__dict__,
			{"db": Mock(get_single_value=Mock(return_value=7))},
		):
			start, end = slot_availability._clamp_couple_date_discovery_range(
				"2026-08-10",
				"2027-08-10",
			)

		self.assertEqual(start, date(2026, 8, 10))
		self.assertEqual(end, date(2026, 8, 17))

	@patch.object(slot_availability, "get_projected_couple_available_slots")
	def test_detailed_couple_search_rejects_multi_day_ranges(self, projected_slots):
		with (
			patch.object(slot_availability, "_", side_effect=lambda message: message),
			patch.object(
				slot_availability.frappe,
				"throw",
				side_effect=ValueError("single date required"),
			),
			self.assertRaisesRegex(ValueError, "single date required"),
		):
			slot_availability.get_couple_available_time_slots(
				service_type_1="SERVICE-1",
				service_type_2="SERVICE-2",
				duration_1=45,
				duration_2=60,
				start_date="2026-08-10",
				end_date="2026-08-12",
			)

		projected_slots.assert_not_called()

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
