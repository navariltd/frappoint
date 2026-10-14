from datetime import date, time
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from frappoint.frappoint.api import booking_desk


def _member(index: int, service_type: str, provider: str, end_time: time) -> dict:
	return {
		"service_type": service_type,
		"appointment_date": date(2026, 8, 10),
		"start_time": time(9),
		"end_time": end_time,
		"provider": provider,
		"service_unit": None,
		"duration": 45 if index == 1 else 60,
		"amount": 100 if index == 1 else 150,
		"currency": "KES",
	}


class TestBookingDeskCoupleHelpers(TestCase):
	def test_exact_projector_candidate_accepts_independent_end_times(self):
		member_1 = _member(1, "SERVICE-1", "PROVIDER-1", time(9, 45))
		member_2 = _member(2, "SERVICE-2", "PROVIDER-2", time(10))
		candidate = {
			"date": date(2026, 8, 10),
			"start_time": time(9),
			"guest_1": {
				"end_time": time(9, 45),
				"provider": "PROVIDER-1",
				"service_unit": None,
			},
			"guest_2": {
				"end_time": time(10),
				"provider": "PROVIDER-2",
				"service_unit": None,
			},
		}

		with patch.object(booking_desk, "get_projected_couple_available_slots", return_value=[candidate]):
			booking_desk._validate_couple_members_against_projector(member_1, member_2)

	def test_projector_validation_rejects_a_provider_unit_pair_not_returned(self):
		member_1 = _member(1, "SERVICE-1", "PROVIDER-1", time(9, 45))
		member_2 = _member(2, "SERVICE-2", "PROVIDER-2", time(10))

		with (
			patch.object(booking_desk, "get_projected_couple_available_slots", return_value=[]),
			patch.object(booking_desk, "_", side_effect=lambda message: message),
			patch.object(frappe, "throw", side_effect=frappe.ValidationError),
		):
			with self.assertRaises(frappe.ValidationError):
				booking_desk._validate_couple_members_against_projector(member_1, member_2)

	def test_booking_items_must_cover_both_selected_services_and_prices(self):
		booking = SimpleNamespace(
			currency="KES",
			items=[
				SimpleNamespace(
					service_type="SERVICE-1",
					rate=100,
					currency="KES",
					qty=2,
					cancelled_qty=0,
				)
			],
		)
		members = [
			_member(1, "SERVICE-1", "PROVIDER-1", time(9, 45)),
			{
				**_member(2, "SERVICE-1", "PROVIDER-2", time(10)),
				"amount": 100,
			},
		]

		booking_desk._validate_couple_booking_items(booking, members)
		booking.items[0].qty = 1
		with (
			patch.object(booking_desk, "_", side_effect=lambda message: message),
			patch.object(frappe, "throw", side_effect=frappe.ValidationError),
		):
			with self.assertRaises(frappe.ValidationError):
				booking_desk._validate_couple_booking_items(booking, members)
