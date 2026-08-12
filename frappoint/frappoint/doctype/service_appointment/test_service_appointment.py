# Copyright (c) 2025, Navari LTD and Contributors
# See license.txt

from datetime import date, datetime, time
from types import MethodType, SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from frappoint.frappoint.doctype.service_appointment.service_appointment import (
	ServiceAppointment,
	cancel_appointment,
)


class TestServiceAppointment(TestCase):
	def test_direct_submit_of_couple_member_is_rejected(self):
		appointment = SimpleNamespace(
			couple_appointment_id="APT-SECONDARY",
			flags=SimpleNamespace(),
		)
		with (
			patch(
				"frappoint.frappoint.doctype.service_appointment.service_appointment._",
				side_effect=lambda message: message,
			),
			patch.object(frappe, "throw", side_effect=frappe.ValidationError),
		):
			with self.assertRaises(frappe.ValidationError):
				ServiceAppointment.before_submit(appointment)

	def test_couple_confirmation_savepoint_precedes_first_submit(self):
		events = []

		def submit_primary():
			events.append("primary_submit")
			raise RuntimeError("linked submit failed")

		primary = SimpleNamespace(
			name="APT-PRIMARY",
			couple_appointment_id="APT-SECONDARY",
			is_primary_in_couple=1,
			docstatus=0,
			status="Open",
			flags=SimpleNamespace(),
			submit=submit_primary,
		)
		secondary = SimpleNamespace(
			name="APT-SECONDARY",
			couple_appointment_id="APT-PRIMARY",
			is_primary_in_couple=0,
			docstatus=0,
			status="Open",
			flags=SimpleNamespace(),
		)
		caller = SimpleNamespace(name=primary.name, couple_appointment_id=secondary.name)
		database = SimpleNamespace(
			savepoint=lambda name: events.append(("savepoint", name)),
			sql=lambda *args, **kwargs: events.append("appointment_locks"),
			rollback=MagicMock(),
		)

		with (
			patch.object(frappe, "db", database),
			patch.object(
				frappe,
				"get_doc",
				side_effect=lambda doctype, name: {
					primary.name: primary,
					secondary.name: secondary,
				}[name],
			),
		):
			with self.assertRaisesRegex(RuntimeError, "linked submit failed"):
				ServiceAppointment._confirm_couple_appointments(caller, savepoint="outer_pair_submit")

		self.assertEqual(
			events[:3],
			[("savepoint", "outer_pair_submit"), "appointment_locks", "primary_submit"],
		)
		database.rollback.assert_called_once_with(save_point="outer_pair_submit")

	def test_pair_insert_can_defer_calendar_and_resource_side_effects(self):
		appointment = SimpleNamespace(
			flags=SimpleNamespace(skip_calendar_event=True, skip_resource_allocation=True),
			insert_calendar_event=MagicMock(),
			sync_resource_allocations=MagicMock(),
		)

		ServiceAppointment.after_insert(appointment)

		appointment.insert_calendar_event.assert_not_called()
		appointment.sync_resource_allocations.assert_not_called()

	def test_couple_configuration_allows_individual_end_times_and_providers(self):
		appointment = SimpleNamespace(
			name="APT-PRIMARY",
			booking_id="BOOKING-1",
			appointment_date=date(2026, 8, 10),
			start_time=time(9),
			end_time=time(9, 45),
			appointment_provider="PROVIDER-1",
			service_unit="ROOM-1",
			couple_appointment_id="APT-SECONDARY",
			is_primary_in_couple=1,
			flags=SimpleNamespace(skip_couple_validation=False),
		)
		linked = frappe._dict(
			name="APT-SECONDARY",
			booking_id="BOOKING-1",
			appointment_date=date(2026, 8, 10),
			start_time=time(9),
			appointment_provider="PROVIDER-2",
			service_unit="ROOM-2",
			couple_appointment_id="APT-PRIMARY",
			is_primary_in_couple=0,
			docstatus=0,
		)

		with patch.object(frappe, "db", SimpleNamespace(get_value=lambda *args, **kwargs: linked)):
			ServiceAppointment.validate_couple_configuration(appointment)

	def test_couple_configuration_rejects_non_overlapping_shared_unit(self):
		appointment = SimpleNamespace(
			name="APT-PRIMARY",
			booking_id="BOOKING-1",
			appointment_date=date(2026, 8, 10),
			start_time=time(9),
			appointment_provider="PROVIDER-1",
			service_unit="ROOM-1",
			couple_appointment_id="APT-SECONDARY",
			is_primary_in_couple=1,
			flags=SimpleNamespace(skip_couple_validation=False),
		)
		linked = frappe._dict(
			name="APT-SECONDARY",
			booking_id="BOOKING-1",
			appointment_date=date(2026, 8, 10),
			start_time=time(9),
			appointment_provider="PROVIDER-2",
			service_unit="ROOM-1",
			couple_appointment_id="APT-PRIMARY",
			is_primary_in_couple=0,
			docstatus=0,
		)

		def get_value(doctype, *args, **kwargs):
			if doctype == "Service Appointment":
				return linked
			return frappe._dict(allow_overlap=0, capacity=2)

		with (
			patch.object(frappe, "db", SimpleNamespace(get_value=get_value)),
			patch(
				"frappoint.frappoint.doctype.service_appointment.service_appointment._",
				side_effect=lambda message: message,
			),
			patch.object(frappe, "throw", side_effect=frappe.ValidationError),
		):
			with self.assertRaises(frappe.ValidationError):
				ServiceAppointment.validate_couple_configuration(appointment)

	def test_allocation_payload_reserves_each_services_buffer_envelope(self):
		appointment = SimpleNamespace(
			appointment_provider="PROVIDER-1",
			appointment_date=date(2026, 8, 10),
			start_time=time(9, 10),
			end_time=time(9, 55),
			service_unit="ROOM-1",
		)
		appointment._get_buffer_minutes = lambda: (10, 5)

		allocations = ServiceAppointment._build_allocation_payloads(appointment)

		self.assertEqual(len(allocations), 2)
		for allocation in allocations:
			self.assertEqual(allocation["start_time"], "09:00:00")
			self.assertEqual(allocation["end_time"], "10:00:00")
			self.assertEqual(allocation["appointment_start_time"], time(9, 10))
			self.assertEqual(allocation["appointment_end_time"], time(9, 55))

	def test_cancelling_appointment_with_submitted_payment_shows_actionable_message(self):
		appointment = SimpleNamespace(name="TEST-APPOINTMENT", docstatus=1, status="Confirmed")

		with (
			patch.object(frappe, "get_doc", return_value=appointment),
			patch.object(frappe, "db", SimpleNamespace(exists=lambda *args, **kwargs: "PAY-0001")),
			patch(
				"frappoint.frappoint.doctype.service_appointment.service_appointment._",
				side_effect=lambda message: message,
			),
			patch.object(frappe, "throw", side_effect=frappe.ValidationError) as throw,
		):
			with self.assertRaises(frappe.ValidationError):
				cancel_appointment("TEST-APPOINTMENT")

		throw.assert_called_once_with(
			"This appointment has a submitted payment and cannot be cancelled. "
			"Cancel the linked payment from the Desk first, then cancel the appointment."
		)

	def test_past_appointment_is_allowed_when_enabled_in_settings(self):
		appointment = SimpleNamespace(
			appointment_date=date(2020, 1, 1),
			start_time=time(9),
			end_time=time(10),
		)

		with (
			patch.object(
				frappe,
				"get_cached_doc",
				return_value=SimpleNamespace(allow_past_booking=1),
			),
			patch(
				"frappoint.frappoint.doctype.service_appointment.service_appointment.now_datetime",
				return_value=datetime(2025, 1, 1),
			),
			patch(
				"frappoint.frappoint.doctype.service_appointment.service_appointment._",
				side_effect=lambda message: message,
			),
			patch.object(frappe, "throw") as throw,
		):
			ServiceAppointment.validate_appointment_date_and_times(appointment)

		throw.assert_not_called()

	def test_past_appointment_is_rejected_when_disabled_in_settings(self):
		appointment = SimpleNamespace(
			appointment_date=date(2020, 1, 1),
			start_time=time(9),
			end_time=time(10),
		)

		with (
			patch.object(
				frappe,
				"get_cached_doc",
				return_value=SimpleNamespace(allow_past_booking=0),
			),
			patch(
				"frappoint.frappoint.doctype.service_appointment.service_appointment.now_datetime",
				return_value=datetime(2025, 1, 1),
			),
			patch(
				"frappoint.frappoint.doctype.service_appointment.service_appointment._",
				side_effect=lambda message: message,
			),
			patch.object(frappe, "throw") as throw,
		):
			ServiceAppointment.validate_appointment_date_and_times(appointment)

		throw.assert_called_once_with("You cannot schedule an appointment in the past")

	def test_recalculate_outstanding_subtracts_payments_and_appointment_discount(self):
		appointment = SimpleNamespace(
			name="TEST-APPOINTMENT",
			booking_id=None,
			total_amount=100,
			discount_amount=10,
		)
		appointment.get_discount_amount_for_outstanding = MethodType(
			ServiceAppointment.get_discount_amount_for_outstanding, appointment
		)

		def get_value(doctype, *args, **kwargs):
			return 30 if doctype == "Service Appointment Payment Reference" else 20

		with patch.object(frappe, "db", SimpleNamespace(get_value=get_value)):
			ServiceAppointment.recalculate_outstanding_from_payments(appointment)

		self.assertEqual(appointment.outstanding_amount, 40)

	def test_recalculate_outstanding_includes_booking_coupon_share(self):
		appointment = SimpleNamespace(
			name="TEST-APPOINTMENT",
			booking_id="TEST-BOOKING",
			total_amount=100,
			discount_amount=0,
		)
		appointment.get_discount_amount_for_outstanding = MethodType(
			ServiceAppointment.get_discount_amount_for_outstanding, appointment
		)

		def get_value(doctype, *args, **kwargs):
			if doctype == "Service Appointment Payment Reference":
				return 40
			if doctype == "Service Appointment Payment":
				return 0
			if doctype == "Service Booking":
				return frappe._dict(
					booking_discount_amount=40,
					subtotal=200,
					appointment_discount_total=0,
				)
			return None

		with patch.object(frappe, "db", SimpleNamespace(get_value=get_value)):
			ServiceAppointment.recalculate_outstanding_from_payments(appointment)

		self.assertEqual(appointment.outstanding_amount, 40)

	def test_recalculate_outstanding_includes_payment_being_submitted(self):
		appointment = SimpleNamespace(
			name="TEST-APPOINTMENT",
			booking_id="TEST-BOOKING",
			total_amount=10000,
			discount_amount=0,
		)
		appointment.get_discount_amount_for_outstanding = MethodType(
			ServiceAppointment.get_discount_amount_for_outstanding, appointment
		)

		def get_value(doctype, *args, **kwargs):
			if doctype in {
				"Service Appointment Payment Reference",
				"Service Appointment Payment",
			}:
				return 0
			if doctype == "Service Booking":
				return frappe._dict(
					booking_discount_amount=7500,
					subtotal=10000,
					appointment_discount_total=0,
				)
			return None

		with patch.object(frappe, "db", SimpleNamespace(get_value=get_value)):
			ServiceAppointment.recalculate_outstanding_from_payments(
				appointment,
				current_payment_name="TEST-PAYMENT",
				current_paid_amount=2500,
			)

		self.assertEqual(appointment.outstanding_amount, 0)
