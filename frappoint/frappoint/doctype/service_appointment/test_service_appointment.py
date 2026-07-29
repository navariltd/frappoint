# Copyright (c) 2025, Navari LTD and Contributors
# See license.txt

from datetime import date, datetime, time
from types import MethodType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from frappoint.frappoint.doctype.service_appointment.service_appointment import ServiceAppointment


class TestServiceAppointment(TestCase):
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
