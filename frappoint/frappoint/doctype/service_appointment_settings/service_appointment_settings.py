# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ServiceAppointmentSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappoint.frappoint.doctype.service_type_payment_gateway.service_type_payment_gateway import (
			ServiceTypePaymentGateway,
		)

		allow_past_booking: DF.Check
		appointment_confirmation: DF.Check
		appointment_confirmation_msg: DF.SmallText | None
		appointment_reminder: DF.Check
		appointment_reminder_msg: DF.SmallText | None
		auto_create_service_items: DF.Check
		auto_issue_consumables: DF.Check
		buffer_after: DF.Int
		buffer_before: DF.Int
		default_google_calendar: DF.Link | None
		default_item_group: DF.Link | None
		default_slot_size: DF.Int
		lead_time_hours: DF.Int
		max_advance_days: DF.Int
		max_past_days: DF.Int
		payment_gateways: DF.Table[ServiceTypePaymentGateway]
	# end: auto-generated types
	pass
