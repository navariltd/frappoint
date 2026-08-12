from datetime import date, time
from unittest import TestCase
from unittest.mock import call, patch

from frappe.utils import get_time

from frappoint.frappoint.services import availability_projector
from frappoint.frappoint.services.availability_projector import _combine_couple_slot_rows


def _slot(
	provider,
	start_time,
	end_time,
	*,
	duration,
	buffer_before=0,
	buffer_after=0,
	service_unit=None,
):
	return {
		"provider": provider,
		"provider_name": provider,
		"service_unit": service_unit,
		"service_unit_name": service_unit,
		"date": date(2026, 8, 10),
		"start_time": get_time(start_time),
		"end_time": get_time(end_time),
		"duration": duration,
		"buffer_before": buffer_before,
		"buffer_after": buffer_after,
		"slot_ids": [],
	}


def _capacity(resource_type, resource, values):
	return {
		(resource_type, resource, date(2026, 8, 10), get_time(slot_time)): remaining
		for slot_time, remaining in values.items()
	}


class TestCoupleAvailabilityProjection(TestCase):
	def test_pairs_only_equal_customer_start_and_preserves_each_duration(self):
		guest_1 = _slot(
			"PROVIDER-1",
			"09:00:00",
			"09:45:00",
			duration=45,
			buffer_before=15,
		)
		guest_2 = _slot(
			"PROVIDER-2",
			"09:00:00",
			"10:00:00",
			duration=60,
			buffer_after=15,
		)
		non_simultaneous = _slot(
			"PROVIDER-3",
			"09:15:00",
			"10:15:00",
			duration=60,
		)

		rows = _combine_couple_slot_rows(
			guest_1_slots=[guest_1],
			guest_2_slots=[guest_2, non_simultaneous],
			service_type_1="SERVICE-45",
			service_type_2="SERVICE-60",
			slot_size_minutes=15,
			remaining_capacity={},
			unit_allows_overlap={},
		)

		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["start_time"], time(9, 0))
		self.assertEqual(rows[0]["guest_1"]["end_time"], time(9, 45))
		self.assertEqual(rows[0]["guest_2"]["end_time"], time(10, 0))
		self.assertEqual(rows[0]["duration_1"], 45)
		self.assertEqual(rows[0]["duration_2"], 60)

	def test_same_provider_requires_capacity_for_both_legs(self):
		guest_1 = _slot("PROVIDER-1", "09:00:00", "09:30:00", duration=30)
		guest_2 = _slot("PROVIDER-1", "09:00:00", "09:30:00", duration=30)
		capacity_one = _capacity(
			"Service Provider",
			"PROVIDER-1",
			{"09:00:00": 1, "09:15:00": 1},
		)

		blocked = _combine_couple_slot_rows(
			[guest_1],
			[guest_2],
			"SERVICE-1",
			"SERVICE-2",
			15,
			capacity_one,
			{},
		)
		self.assertEqual(blocked, [])

		capacity_two = _capacity(
			"Service Provider",
			"PROVIDER-1",
			{"09:00:00": 2, "09:15:00": 2},
		)
		available = _combine_couple_slot_rows(
			[guest_1],
			[guest_2],
			"SERVICE-1",
			"SERVICE-2",
			15,
			capacity_two,
			{},
		)
		self.assertEqual(len(available), 1)

	def test_same_unit_requires_overlap_permission_and_capacity_two(self):
		guest_1 = _slot(
			"PROVIDER-1",
			"09:00:00",
			"09:30:00",
			duration=30,
			service_unit="ROOM-1",
		)
		guest_2 = _slot(
			"PROVIDER-2",
			"09:00:00",
			"09:45:00",
			duration=45,
			service_unit="ROOM-1",
		)
		capacity_two = _capacity(
			"Service Unit",
			"ROOM-1",
			{"09:00:00": 2, "09:15:00": 2, "09:30:00": 2},
		)

		overlap_disabled = _combine_couple_slot_rows(
			[guest_1],
			[guest_2],
			"SERVICE-1",
			"SERVICE-2",
			15,
			capacity_two,
			{"ROOM-1": False},
		)
		self.assertEqual(overlap_disabled, [])

		overlap_enabled = _combine_couple_slot_rows(
			[guest_1],
			[guest_2],
			"SERVICE-1",
			"SERVICE-2",
			15,
			capacity_two,
			{"ROOM-1": True},
		)
		self.assertEqual(len(overlap_enabled), 1)

		insufficient_capacity = dict(capacity_two)
		insufficient_capacity[("Service Unit", "ROOM-1", date(2026, 8, 10), time(9, 15))] = 1
		capacity_blocked = _combine_couple_slot_rows(
			[guest_1],
			[guest_2],
			"SERVICE-1",
			"SERVICE-2",
			15,
			insufficient_capacity,
			{"ROOM-1": True},
		)
		self.assertEqual(capacity_blocked, [])

	def test_different_units_can_be_paired_without_overlap(self):
		guest_1 = _slot(
			"PROVIDER-1",
			"09:00:00",
			"09:30:00",
			duration=30,
			service_unit="ROOM-1",
		)
		guest_2 = _slot(
			"PROVIDER-2",
			"09:00:00",
			"09:30:00",
			duration=30,
			service_unit="ROOM-2",
		)

		rows = _combine_couple_slot_rows(
			[guest_1],
			[guest_2],
			"SERVICE-1",
			"SERVICE-2",
			15,
			{},
			{"ROOM-1": False, "ROOM-2": False},
		)

		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["service_unit_1"], "ROOM-1")
		self.assertEqual(rows[0]["service_unit_2"], "ROOM-2")

	@patch.object(availability_projector, "_get_slot_size_minutes", return_value=15)
	@patch.object(availability_projector, "_get_unit_overlap_map", return_value={})
	@patch.object(availability_projector, "_get_resource_remaining_capacity_map", return_value={})
	@patch.object(availability_projector, "get_available_slots")
	def test_projector_builds_each_leg_with_all_compatible_units(
		self,
		get_available_slots,
		_capacity_map,
		_overlap_map,
		_slot_size,
	):
		guest_1 = _slot("PROVIDER-1", "09:00:00", "09:45:00", duration=45)
		guest_2 = _slot("PROVIDER-2", "09:00:00", "10:00:00", duration=60)
		get_available_slots.side_effect = [[guest_1], [guest_2]]

		rows = availability_projector.get_couple_available_slots(
			service_type_1="SERVICE-1",
			service_type_2="SERVICE-2",
			start_date="2026-08-10",
			end_date="2026-08-10",
			provider_1="PROVIDER-1",
			provider_2="PROVIDER-2",
			duration_1=45,
			duration_2=60,
		)

		self.assertEqual(len(rows), 1)
		self.assertEqual(
			get_available_slots.call_args_list,
			[
				call(
					service_type_id="SERVICE-1",
					start_date=date(2026, 8, 10),
					end_date=date(2026, 8, 10),
					provider_id="PROVIDER-1",
					service_unit_id=None,
					required_duration_minutes=45,
					exclude_appointment_id=None,
					include_all_service_units=True,
				),
				call(
					service_type_id="SERVICE-2",
					start_date=date(2026, 8, 10),
					end_date=date(2026, 8, 10),
					provider_id="PROVIDER-2",
					service_unit_id=None,
					required_duration_minutes=60,
					exclude_appointment_id=None,
					include_all_service_units=True,
				),
			],
		)
