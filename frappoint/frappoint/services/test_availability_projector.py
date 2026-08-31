from datetime import date, time, timedelta
from unittest import TestCase
from unittest.mock import call, patch

from frappe.utils import get_time

from frappoint.frappoint.services import availability_projector
from frappoint.frappoint.services.availability_projector import (
    _combine_couple_slot_rows,
)


def _slot(
    provider,
    start_time,
    end_time,
    *,
    duration,
    buffer_before=0,
    buffer_after=0,
    service_unit=None,
    slot_date=date(2026, 8, 10),
):
    return {
        "provider": provider,
        "provider_name": provider,
        "service_unit": service_unit,
        "service_unit_name": service_unit,
        "date": slot_date,
        "start_time": get_time(start_time),
        "end_time": get_time(end_time),
        "duration": duration,
        "buffer_before": buffer_before,
        "buffer_after": buffer_after,
        "slot_ids": [],
    }


def _capacity(resource_type, resource, values, slot_date=date(2026, 8, 10)):
    return {
        (resource_type, resource, slot_date, get_time(slot_time)): remaining
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
            service_unit="ROOM-1",
        )
        guest_2 = _slot(
            "PROVIDER-2",
            "09:00:00",
            "10:00:00",
            duration=60,
            buffer_after=15,
            service_unit="ROOM-1",
        )
        non_simultaneous = _slot(
            "PROVIDER-3",
            "09:15:00",
            "10:15:00",
            duration=60,
            service_unit="ROOM-1",
        )
        room_capacity = _capacity(
            "Service Unit",
            "ROOM-1",
            {
                "08:45:00": 1,
                "09:00:00": 2,
                "09:15:00": 2,
                "09:30:00": 2,
                "09:45:00": 1,
                "10:00:00": 1,
            },
        )

        rows = _combine_couple_slot_rows(
            guest_1_slots=[guest_1],
            guest_2_slots=[guest_2, non_simultaneous],
            service_type_1="SERVICE-45",
            service_type_2="SERVICE-60",
            slot_size_minutes=15,
            remaining_capacity=room_capacity,
            unit_allows_overlap={"ROOM-1": True},
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["start_time"], time(9, 0))
        self.assertEqual(rows[0]["guest_1"]["end_time"], time(9, 45))
        self.assertEqual(rows[0]["guest_2"]["end_time"], time(10, 0))
        self.assertEqual(rows[0]["duration_1"], 45)
        self.assertEqual(rows[0]["duration_2"], 60)

    def test_same_provider_requires_capacity_for_both_legs(self):
        guest_1 = _slot(
            "PROVIDER-1",
            "09:00:00",
            "09:30:00",
            duration=30,
            service_unit="ROOM-1",
        )
        guest_2 = _slot(
            "PROVIDER-1",
            "09:00:00",
            "09:30:00",
            duration=30,
            service_unit="ROOM-1",
        )
        capacity_one = _capacity(
            "Service Provider",
            "PROVIDER-1",
            {"09:00:00": 1, "09:15:00": 1},
        )
        room_capacity = _capacity(
            "Service Unit",
            "ROOM-1",
            {"09:00:00": 2, "09:15:00": 2},
        )

        blocked = _combine_couple_slot_rows(
            [guest_1],
            [guest_2],
            "SERVICE-1",
            "SERVICE-2",
            15,
            {**capacity_one, **room_capacity},
            {"ROOM-1": True},
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
            {**capacity_two, **room_capacity},
            {"ROOM-1": True},
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
        insufficient_capacity[
            ("Service Unit", "ROOM-1", date(2026, 8, 10), time(9, 15))
        ] = 1
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

    def test_different_units_are_rejected_for_couple_booking(self):
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

        with patch.object(
            availability_projector,
            "_reserved_counter_slot_times",
            wraps=availability_projector._reserved_counter_slot_times,
        ) as reserved_slots:
            rows = _combine_couple_slot_rows(
                [guest_1],
                [guest_2],
                "SERVICE-1",
                "SERVICE-2",
                15,
                {},
                {"ROOM-1": False, "ROOM-2": False},
            )

        self.assertEqual(rows, [])
        reserved_slots.assert_not_called()

    def test_optional_date_limit_counts_only_eligible_candidates_and_is_deterministic(self):
        first_date = date(2026, 8, 10)
        second_date = date(2026, 8, 11)
        guest_1_slots = [
            _slot(
                provider,
                "09:00:00",
                "09:30:00",
                duration=30,
                service_unit="ROOM-1",
                slot_date=slot_date,
            )
            for slot_date in (second_date, first_date)
            for provider in ("PROVIDER-B", "PROVIDER-A")
        ]
        guest_2_slots = [
            _slot(
                provider,
                "09:00:00",
                "09:30:00",
                duration=30,
                service_unit="ROOM-1",
                slot_date=slot_date,
            )
            for slot_date in (second_date, first_date)
            for provider in ("PROVIDER-D", "PROVIDER-C")
        ]
        remaining_capacity = {}
        for slot_date in (first_date, second_date):
            remaining_capacity.update(
                _capacity(
                    "Service Unit",
                    "ROOM-1",
                    {"09:00:00": 2, "09:15:00": 2},
                    slot_date=slot_date,
                )
            )

        inspected = []

        def accept_provider_b(candidate):
            inspected.append(candidate["candidate_id"])
            return candidate["provider_1"] == "PROVIDER-B"

        accept_provider_b.allows_leg = lambda _leg_name, _row: True

        limited = _combine_couple_slot_rows(
            guest_1_slots,
            guest_2_slots,
            "SERVICE-1",
            "SERVICE-2",
            15,
            remaining_capacity,
            {"ROOM-1": True},
            candidate_filter=accept_provider_b,
            max_candidates_per_date=1,
        )

        self.assertEqual(
            [(row["date"], row["provider_1"], row["provider_2"]) for row in limited],
            [
                (first_date, "PROVIDER-B", "PROVIDER-C"),
                (second_date, "PROVIDER-B", "PROVIDER-C"),
            ],
        )
        self.assertIn("PROVIDER-A", inspected[0])

        complete = _combine_couple_slot_rows(
            guest_1_slots,
            guest_2_slots,
            "SERVICE-1",
            "SERVICE-2",
            15,
            remaining_capacity,
            {"ROOM-1": True},
        )
        self.assertEqual(len(complete), 8)

    def test_date_limit_avoids_the_provider_unit_cartesian_product(self):
        dates = [date(2026, 8, 10) + timedelta(days=offset) for offset in range(30)]
        providers_1 = [f"PROVIDER-1-{index:02d}" for index in range(42)]
        providers_2 = [f"PROVIDER-2-{index:02d}" for index in range(42)]
        units = [f"ROOM-{index:02d}" for index in range(20)]

        guest_1_slots = [
            _slot(
                provider,
                "09:00:00",
                "09:30:00",
                duration=30,
                service_unit=unit,
                slot_date=slot_date,
            )
            for slot_date in dates
            for provider in providers_1
            for unit in units
        ]
        guest_2_slots = [
            _slot(
                provider,
                "09:00:00",
                "09:30:00",
                duration=30,
                service_unit=unit,
                slot_date=slot_date,
            )
            for slot_date in dates
            for provider in providers_2
            for unit in units
        ]
        remaining_capacity = {}
        for slot_date in dates:
            for unit in units:
                remaining_capacity.update(
                    _capacity(
                        "Service Unit",
                        unit,
                        {"09:00:00": 2, "09:15:00": 2},
                        slot_date=slot_date,
                    )
                )

        theoretical_pair_count = (
            len(dates) * len(units) * len(providers_1) * len(providers_2)
        )
        self.assertGreater(theoretical_pair_count, 1_000_000)

        with patch.object(
            availability_projector,
            "_reserved_counter_slot_times",
            wraps=availability_projector._reserved_counter_slot_times,
        ) as reserved_slots:
            rows = _combine_couple_slot_rows(
                guest_1_slots,
                guest_2_slots,
                "SERVICE-1",
                "SERVICE-2",
                15,
                remaining_capacity,
                dict.fromkeys(units, True),
                max_candidates_per_date=1,
            )

        self.assertEqual(len(rows), len(dates))
        self.assertEqual(reserved_slots.call_count, len(dates) * 2)

        insufficient_capacity = {}
        for slot_date in dates:
            for unit in units:
                insufficient_capacity.update(
                    _capacity(
                        "Service Unit",
                        unit,
                        {"09:00:00": 1, "09:15:00": 1},
                        slot_date=slot_date,
                    )
                )

        with patch.object(
            availability_projector,
            "_shared_resource_has_capacity",
            wraps=availability_projector._shared_resource_has_capacity,
        ) as capacity_checks:
            blocked_rows = _combine_couple_slot_rows(
                guest_1_slots,
                guest_2_slots,
                "SERVICE-1",
                "SERVICE-2",
                15,
                insufficient_capacity,
                dict.fromkeys(units, True),
                max_candidates_per_date=1,
            )

        self.assertEqual(blocked_rows, [])
        self.assertEqual(capacity_checks.call_count, len(dates) * len(units))

        class RejectEveryLeg:
            def __init__(self):
                self.final_candidate_checks = 0

            def allows_leg(self, _leg_name, _row):
                return False

            def __call__(self, _candidate):
                self.final_candidate_checks += 1
                return True

        reject_every_leg = RejectEveryLeg()
        with (
            patch.object(availability_projector, "_shared_resource_has_capacity") as capacity_checks,
            patch.object(availability_projector, "_build_couple_guest_row") as pair_leg_builds,
        ):
            rejected_rows = _combine_couple_slot_rows(
                guest_1_slots,
                guest_2_slots,
                "SERVICE-1",
                "SERVICE-2",
                15,
                remaining_capacity,
                dict.fromkeys(units, True),
                candidate_filter=reject_every_leg,
                max_candidates_per_date=1,
            )

        self.assertEqual(rejected_rows, [])
        capacity_checks.assert_not_called()
        pair_leg_builds.assert_not_called()
        self.assertEqual(reject_every_leg.final_candidate_checks, 0)

    @patch.object(availability_projector, "_get_slot_size_minutes", return_value=15)
    @patch.object(availability_projector, "_get_unit_overlap_map")
    @patch.object(
        availability_projector, "_get_resource_remaining_capacity_map", return_value={}
    )
    @patch.object(availability_projector, "get_available_slots")
    def test_projector_builds_each_leg_with_all_compatible_units(
        self,
        get_available_slots,
        _capacity_map,
        _overlap_map,
        _slot_size,
    ):
        guest_1 = _slot(
            "PROVIDER-1",
            "09:00:00",
            "09:45:00",
            duration=45,
            service_unit="ROOM-1",
        )
        guest_2 = _slot(
            "PROVIDER-2",
            "09:00:00",
            "10:00:00",
            duration=60,
            service_unit="ROOM-1",
        )
        get_available_slots.side_effect = [[guest_1], [guest_2]]
        _capacity_map.return_value = _capacity(
            "Service Unit",
            "ROOM-1",
            {"09:00:00": 2, "09:15:00": 2, "09:30:00": 2, "09:45:00": 1},
        )
        _overlap_map.return_value = {"ROOM-1": True}

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
