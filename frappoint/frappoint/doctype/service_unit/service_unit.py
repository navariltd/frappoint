# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate, nowdate

from frappoint.frappoint.services.availability_projector import enqueue_targeted_counter_refresh


class ServiceUnit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_appointments: DF.Check
		allow_overlap: DF.Check
		capacity: DF.Int
		company: DF.Link
		disabled: DF.Check
		is_group: DF.Check
		lft: DF.Int
		location: DF.Link | None
		old_parent: DF.Link | None
		parent_service_unit: DF.Link | None
		rgt: DF.Int
		unit_name: DF.Data
		unit_type: DF.Link
	# end: auto-generated types

	def on_update(self):
		previous = self.get_doc_before_save()
		availability_fields = ("capacity", "allow_overlap", "allow_appointments", "disabled")
		if not previous or not any(self.has_value_changed(field) for field in availability_fields):
			return

		settings = frappe.get_cached_doc("Service Appointment Settings")
		today = getdate(nowdate())
		enqueue_targeted_counter_refresh(
			start_date=add_days(today, -1),
			end_date=add_days(today, cint(settings.max_advance_days or 30)),
			service_unit=self.name,
		)
