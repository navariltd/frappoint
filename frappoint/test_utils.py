from datetime import datetime
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from frappoint import utils
from frappoint.frappoint.services import booking_transaction_service


class TestPendingPaymentHoldExpiry(TestCase):
	def test_expired_couple_is_released_and_closed_as_one_group(self):
		primary = SimpleNamespace(
			name="APT-PRIMARY",
			booking_id="BOOKING-1",
			couple_appointment_id="APT-SECONDARY",
			is_primary_in_couple=1,
			docstatus=0,
			status="Pending Payment",
			payment_expires_at=datetime(2026, 8, 6, 9),
			confirmation_required_amount=50,
			recalculate_outstanding_from_payments=MagicMock(),
			set_confirmation_targets=MagicMock(),
			get_paid_amount=MagicMock(return_value=0),
			db_set=MagicMock(),
		)
		secondary = SimpleNamespace(
			name="APT-SECONDARY",
			booking_id="BOOKING-1",
			couple_appointment_id="APT-PRIMARY",
			is_primary_in_couple=0,
			docstatus=0,
			status="Open",
			payment_expires_at=datetime(2026, 8, 6, 9, 5),
			confirmation_required_amount=50,
			recalculate_outstanding_from_payments=MagicMock(),
			set_confirmation_targets=MagicMock(),
			get_paid_amount=MagicMock(return_value=0),
			db_set=MagicMock(),
		)
		booking = SimpleNamespace(sync_financial_snapshot=MagicMock())
		database = SimpleNamespace(
			savepoint=MagicMock(),
			sql=MagicMock(),
			rollback=MagicMock(),
			commit=MagicMock(),
		)
		candidate = frappe._dict(
			name=primary.name,
			booking_id=primary.booking_id,
			couple_appointment_id=secondary.name,
		)

		def get_doc(doctype, name):
			if doctype == "Service Booking":
				return booking
			return {primary.name: primary, secondary.name: secondary}[name]

		with (
			patch.object(frappe, "db", database),
			patch.object(frappe, "get_all", return_value=[candidate]),
			patch.object(frappe, "get_doc", side_effect=get_doc),
			patch.object(
				utils,
				"now_datetime",
				return_value=datetime(2026, 8, 6, 9, 10),
			),
			patch.object(
				booking_transaction_service,
				"release_couple_appointment_allocations",
			) as release_couple,
			patch.object(
				booking_transaction_service,
				"release_capacity_for_allocations",
			) as release_single,
		):
			result = utils.expire_pending_payment_holds()

		release_couple.assert_called_once_with(
			appointment_names=[primary.name, secondary.name],
			target_status="Released",
		)
		release_single.assert_not_called()
		primary.db_set.assert_called_once_with(
			{"status": "Closed", "payment_expires_at": None}, update_modified=False
		)
		secondary.db_set.assert_called_once_with(
			{"status": "Closed", "payment_expires_at": None}, update_modified=False
		)
		self.assertEqual(result, "Expired 2 unpaid appointments")
