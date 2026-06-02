# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

if TYPE_CHECKING:
	from frappe.types import DF


class ResourceAvailabilityCounter(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	if TYPE_CHECKING:
		block_reason: DF.Text | None
		consumed_capacity: DF.Float
		counter_date: DF.Date
		counter_slot_time: DF.Time
		created_at: DF.Datetime | None
		is_blocked: DF.Check
		last_updated_at: DF.Datetime | None
		max_capacity: DF.Float
		remaining_capacity: DF.Float
		resource_reference: DF.DynamicLink
		resource_type: DF.Literal["Service Provider", "Service Unit", "Equipment"]
		slot_duration_minutes: DF.Int
		source_reference: DF.Text | None
		source_type: DF.Literal["Shift", "Appointment", "Maintenance", "Break"] | None

	# end: auto-generated types

	def validate(self):
		"""Validate counter record."""
		# Validate capacity values
		if self.max_capacity <= 0:
			frappe.throw(_("Max capacity must be greater than 0"))

		if self.consumed_capacity < 0:
			frappe.throw(_("Consumed capacity must be non-negative"))

		if self.consumed_capacity > self.max_capacity:
			frappe.throw(_("Consumed capacity cannot exceed max capacity"))

		# Validate slot duration is positive
		if self.slot_duration_minutes <= 0:
			frappe.throw(_("Slot duration must be positive"))

		# Validate resource_reference exists
		if self.resource_type and self.resource_reference:
			if not frappe.db.exists(self.resource_type, self.resource_reference):
				frappe.throw(
					_("Resource {0} of type {1} does not exist").format(
						self.resource_reference, self.resource_type
					)
				)

		# Set created_at on first save
		if not self.created_at:
			self.created_at = now_datetime()

		# Always update last_updated_at
		self.last_updated_at = now_datetime()

	def before_save(self):
		"""Before save operations."""
		# Compute remaining_capacity
		self.remaining_capacity = self.max_capacity - self.consumed_capacity

	@property
	def is_available(self) -> bool:
		"""Check if this slot has available capacity."""
		return self.remaining_capacity > 0 and not self.is_blocked

	def get_available_capacity(self) -> float:
		"""Get available capacity (0 if blocked)."""
		if self.is_blocked:
			return 0.0
		return max(0.0, self.remaining_capacity)

	@staticmethod
	def get_counter(
		resource_type: str, resource_reference: str, counter_date: str, counter_slot_time: str
	) -> Document | None:
		"""Fetch a counter record by key fields."""
		try:
			return frappe.get_doc(
				"Resource Availability Counter",
				frappe.db.get_value(
					"Resource Availability Counter",
					{
						"resource_type": resource_type,
						"resource_reference": resource_reference,
						"counter_date": counter_date,
						"counter_slot_time": counter_slot_time,
					},
				),
			)
		except frappe.DoesNotExistError:
			return None

	@staticmethod
	def upsert_counter(
		resource_type: str,
		resource_reference: str,
		counter_date: str,
		counter_slot_time: str,
		max_capacity: float,
		consumed_capacity: float,
		slot_duration_minutes: int = 15,
		is_blocked: bool = False,
		source_type: str | None = None,
		source_reference: str | None = None,
	) -> "ResourceAvailabilityCounter":
		"""Upsert counter record."""
		# Try to get existing counter
		existing = ResourceAvailabilityCounter.get_counter(
			resource_type, resource_reference, counter_date, counter_slot_time
		)

		if existing:
			# Update existing
			existing.max_capacity = max_capacity
			existing.consumed_capacity = consumed_capacity
			existing.is_blocked = is_blocked
			existing.source_type = source_type
			existing.source_reference = source_reference
			existing.save(ignore_permissions=True)
			return existing
		else:
			# Create new
			counter = frappe.new_doc("Resource Availability Counter")
			counter.resource_type = resource_type
			counter.resource_reference = resource_reference
			counter.counter_date = counter_date
			counter.counter_slot_time = counter_slot_time
			counter.max_capacity = max_capacity
			counter.consumed_capacity = consumed_capacity
			counter.slot_duration_minutes = slot_duration_minutes
			counter.is_blocked = is_blocked
			counter.source_type = source_type
			counter.source_reference = source_reference
			counter.insert(ignore_permissions=True)
			return counter
