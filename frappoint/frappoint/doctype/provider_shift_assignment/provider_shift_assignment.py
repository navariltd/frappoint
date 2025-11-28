# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_link_to_form

from ..appointment_provider_slot.appointment_provider_slot import generate_for_shift


class MultipleShiftError(frappe.ValidationError):
	pass


class ProviderShiftAssignment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappoint.frappoint.doctype.provider_shift_assignment_day.provider_shift_assignment_day import (
			ProviderShiftAssignmentDay,
		)

		amended_from: DF.Link | None
		company: DF.Link
		days: DF.TableMultiSelect[ProviderShiftAssignmentDay]
		end_date: DF.Date | None
		provider: DF.Link
		provider_name: DF.Data | None
		repeat_type: DF.Literal["Daily", "Weekly"]
		shift_type: DF.Link
		start_date: DF.Date
		status: DF.Literal["Active", "Inactive"]
	# end: auto-generated types
	pass

	def validate(self):
		self.validate_active_provider()
		if self.end_date:
			self.validate_from_to_dates("start_date", "end_date")
		self.validate_overlapping_shifts()

	def on_submit(self):
		generate_for_shift(self.name)

	def on_update_after_submit(self):
		if self.end_date:
			self.validate_from_to_dates("start_date", "end_date")
		self.validate_overlapping_shifts()

		generate_for_shift(self.name)

	def validate_active_provider(self):
		if self.provider and frappe.db.get_value("Appointment Provider", self.provider, "active") == "0":
			frappe.throw(
				_("Transactions cannot be created for an Inactive Appointment Provider {0}.").format(
					get_link_to_form("Appointment Provider", self.provider)
				),
			)

	def validate_overlapping_shifts(self):
		if self.status == "Inactive":
			return

		overlapping_dates = self.get_overlapping_dates()
		if len(overlapping_dates):
			self.validate_same_date_multiple_shifts(overlapping_dates)
			# if dates are overlapping, check if timings are overlapping, else allow
			for d in overlapping_dates:
				if self.has_overlapping_timings(self.shift_type, d.shift_type):
					self.throw_overlap_error(d)

	def validate_same_date_multiple_shifts(self, overlapping_dates):
		# TODO: Consider adding multiple shift assignments
		msg = _("{0} already has an active Shift Assignment {1} for some/all of these dates.").format(
			frappe.bold(self.provider),
			get_link_to_form("Shift Assignment", overlapping_dates[0].name),
		)

		frappe.throw(
			title=_("Multiple Shift Assignments"),
			msg=msg,
			exc=MultipleShiftError,
		)

	def get_overlapping_dates(self):
		if not self.name:
			self.name = "New Provider Shift Assignment"

		shift = frappe.qb.DocType("Provider Shift Assignment")
		query = (
			frappe.qb.from_(shift)
			.select(shift.name, shift.shift_type, shift.docstatus, shift.status)
			.where(
				(shift.provider == self.provider)
				& (shift.docstatus == 1)
				& (shift.name != self.name)
				& (shift.status == "Active")
				& ((shift.end_date >= self.start_date) | (shift.end_date.isnull()))
			)
		)

		if self.end_date:
			query = query.where(shift.start_date <= self.end_date)

		return query.run(as_dict=True)

	@staticmethod
	def has_overlapping_timings(shift_1: str, shift_2: str) -> bool:
		"""
		Accepts two shift types and checks whether their timings are overlapping
		"""

		s1 = frappe.db.get_value("Provider Shift Type", shift_1, ["start_time", "end_time"], as_dict=True)
		s2 = frappe.db.get_value("Provider Shift Type", shift_2, ["start_time", "end_time"], as_dict=True)

		for d in [s1, s2]:
			if d.end_time <= d.start_time:
				d.end_time += timedelta(days=1)

		return s1.end_time > s2.start_time and s1.start_time < s2.end_time
