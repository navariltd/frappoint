from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_time, getdate

from frappoint.frappoint.services.availability_projector import enqueue_targeted_counter_refresh


class ServiceProviderUnavailability(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		all_day: DF.Check
		employee: DF.Link | None
		from_date: DF.Date
		from_time: DF.Time | None
		notes: DF.SmallText | None
		provider: DF.Link
		provider_name: DF.Data | None
		reason: DF.Literal["Sick", "Off Day", "Training", "Emergency", "Leave", "Other"]
		source: DF.Literal["Manual", "HRMS Leave Application", "HRMS Attendance"]
		source_doctype: DF.Link | None
		source_name: DF.DynamicLink | None
		status: DF.Literal["Active", "Cancelled"]
		to_date: DF.Date
		to_time: DF.Time | None
	# end: auto-generated types

	def validate(self):
		self._set_employee_from_provider()
		self._validate_dates()
		self._validate_times()

	def after_insert(self):
		self._enqueue_counter_refresh()

	def on_submit(self):
		self.status = "Active"
		self.db_set("status", "Active", update_modified=False)
		self._enqueue_counter_refresh()

	def on_update(self):
		self._enqueue_previous_counter_refresh()
		self._enqueue_counter_refresh()

	def on_cancel(self):
		self.status = "Cancelled"
		self.db_set("status", "Cancelled", update_modified=False)
		self._enqueue_counter_refresh()

	def on_trash(self):
		self._enqueue_counter_refresh()

	def _set_employee_from_provider(self):
		if not self.provider:
			return
		self.employee = frappe.db.get_value("Service Provider", self.provider, "employee")

	def _validate_dates(self):
		if not self.from_date or not self.to_date:
			return
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date cannot be before From Date."))

	def _validate_times(self):
		if self.all_day:
			self.from_time = None
			self.to_time = None
			return

		if not self.from_time or not self.to_time:
			frappe.throw(_("From Time and To Time are required for partial-day unavailability."))
		if get_time(self.to_time) <= get_time(self.from_time):
			frappe.throw(_("To Time must be after From Time."))

	def _enqueue_counter_refresh(self):
		if not self.provider or not self.from_date or not self.to_date:
			return
		enqueue_targeted_counter_refresh(
			start_date=self.from_date,
			end_date=self.to_date,
			provider=self.provider,
		)

	def _enqueue_previous_counter_refresh(self):
		old_doc = self.get_doc_before_save()
		if (
			not old_doc
			or not old_doc.provider
			or not old_doc.from_date
			or not old_doc.to_date
			or (
				old_doc.provider == self.provider
				and old_doc.from_date == self.from_date
				and old_doc.to_date == self.to_date
			)
		):
			return

		enqueue_targeted_counter_refresh(
			start_date=old_doc.from_date,
			end_date=old_doc.to_date,
			provider=old_doc.provider,
		)
