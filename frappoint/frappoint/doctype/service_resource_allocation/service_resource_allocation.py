# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate, now_datetime

if TYPE_CHECKING:
	from frappe.types import DF


class ServiceResourceAllocation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allocation_date: DF.Date
		allocation_status: DF.Literal["Draft", "Held", "Confirmed", "Released", "Cancelled"]
		appointment_end_time: DF.Time
		appointment_start_time: DF.Time
		buffer_after_minutes: DF.Int
		buffer_before_minutes: DF.Int
		capacity_consumed: DF.Float
		confirmed_at: DF.Datetime | None
		created_at: DF.Datetime | None
		end_time: DF.Time
		is_confirmed: DF.Check
		metadata_json: DF.JSON | None
		naming_series: DF.Literal["SRA-.DD.-.MM.-.YYYY.-.#####"]
		resource_reference: DF.DynamicLink
		resource_type: DF.Literal["Service Provider", "Service Unit", "Equipment"]
		service_appointment: DF.Link
		service_booking: DF.Link | None
		start_time: DF.Time
	# end: auto-generated types

	def validate(self):
		"""Validate allocation record."""
		# Validate time ordering
		if self.start_time >= self.end_time:
			frappe.throw(_("Start time must be before end time"))

		if self.appointment_start_time >= self.appointment_end_time:
			frappe.throw(_("Appointment start time must be before end time"))

		# Validate capacity_consumed is positive
		if self.capacity_consumed <= 0:
			frappe.throw(_("Capacity consumed must be greater than 0"))

		# Validate buffers are non-negative
		if self.buffer_before_minutes and self.buffer_before_minutes < 0:
			frappe.throw(_("Buffer before minutes must be non-negative"))
		if self.buffer_after_minutes and self.buffer_after_minutes < 0:
			frappe.throw(_("Buffer after minutes must be non-negative"))

		# Validate resource_reference exists
		if self.resource_type and self.resource_reference:
			if not frappe.db.exists(self.resource_type, self.resource_reference):
				frappe.throw(
					_("Resource {0} of type {1} does not exist").format(
						self.resource_reference, self.resource_type
					)
				)

		# Validate service_appointment exists
		if not frappe.db.exists("Service Appointment", self.service_appointment):
			frappe.throw(_("Service Appointment {0} does not exist").format(self.service_appointment))

		# Set created_at on first save
		if not self.created_at:
			self.created_at = now_datetime()

	def on_submit(self):
		"""Called when allocation is submitted."""
		# If status is Confirmed, record confirmed_at timestamp
		if self.allocation_status == "Confirmed" and not self.confirmed_at:
			self.confirmed_at = now_datetime()
			self.is_confirmed = True
			self.db_update()

	def before_save(self):
		"""Before save operations."""
		# Auto-set is_confirmed based on status
		if self.allocation_status == "Confirmed":
			self.is_confirmed = True
		else:
			self.is_confirmed = False

	def on_update_after_submit(self):
		"""Called after document is updated post-submission."""
		# If status changed to Confirmed, record confirmed_at
		if self.allocation_status == "Confirmed" and not self.confirmed_at:
			self.confirmed_at = now_datetime()
			frappe.db.set_value(
				"Service Resource Allocation",
				self.name,
				{"confirmed_at": self.confirmed_at, "is_confirmed": True},
			)
