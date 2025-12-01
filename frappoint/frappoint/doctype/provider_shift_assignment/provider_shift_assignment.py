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

	def validate(self):
		self.validate_active_provider()
		if self.end_date:
			self.validate_from_to_dates("start_date", "end_date")
		self.validate_overlapping_shifts()

	def before_update_after_submit(self):
		"""Store old values and validate before update"""
		if not self.is_new() and self.docstatus == 1:
			old_doc = frappe.get_doc("Provider Shift Assignment", self.name)

			self.flags.old_shift_type = old_doc.shift_type
			self.flags.old_start_date = old_doc.start_date
			self.flags.old_end_date = old_doc.end_date
			self.flags.old_repeat_type = old_doc.repeat_type
			self.flags.old_status = old_doc.status

			if old_doc.repeat_type == "Weekly":
				self.flags.old_days = {d.weekday for d in old_doc.days}

			if self.repeat_type == "Weekly" and old_doc.repeat_type == "Weekly":
				self.validate_weekday_changes(old_doc)

	def on_submit(self):
		generate_for_shift(self.name)

	def on_update_after_submit(self):
		if self.end_date:
			self.validate_from_to_dates("start_date", "end_date")
		self.validate_overlapping_shifts()

		if self.status == "Inactive":
			self.deactivate_slots()
			return

		if (
			self.status == "Active"
			and hasattr(self.flags, "old_status")
			and self.flags.old_status == "Inactive"
		):
			frappe.msgprint(_("Shift reactivated. Regenerating slots..."), indicator="green", alert=True)
			generate_for_shift(self.name)
			return

		regeneration_type = self.check_for_slot_regeneration()

		if regeneration_type == "full":
			# Full regeneration needed (shift type, dates changed)
			frappe.msgprint(
				_("Critical shift parameters changed. All slots will be regenerated."),
				indicator="orange",
				alert=True,
			)
			frappe.enqueue(
				"frappoint.frappoint.doctype.appointment_provider_slot.appointment_provider_slot.generate_for_shift",
				shift_assignment=self.name,
				queue="default",
				timeout=300,
				is_async=True,
			)
		elif regeneration_type == "partial":
			# Partial regeneration (only weekdays changed)
			self.handle_weekday_changes()

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

	def validate_weekday_changes(self, old_doc):
		"""Validate that removed weekdays don't have booked appointments"""
		if self.repeat_type != "Weekly" or old_doc.repeat_type != "Weekly":
			return

		old_days = {d.weekday for d in old_doc.days}
		new_days = {d.weekday for d in self.days}
		removed_days = old_days - new_days

		if not removed_days:
			return

		# Map weekday names to indices
		DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
		removed_indices = [DAYS.index(day) for day in removed_days]

		# Check if any booked appointments exist on removed days
		booked_slots = frappe.db.sql(
			"""
			SELECT
				posting_date,
				start_time,
				end_time,
				service_appointment
			FROM `tabAppointment Provider Slot`
			WHERE shift_assignment = %s
			AND service_appointment IS NOT NULL
			AND service_appointment != ''
			AND DAYOFWEEK(posting_date) - 1 IN %s
			LIMIT 5
		""",
			(self.name, removed_indices),
			as_dict=True,
		)

		if booked_slots:
			# Format the error message with details
			removed_day_names = ", ".join(sorted(removed_days))
			appointment_details = []

			for slot in booked_slots[:3]:  # Show max 3 examples
				appointment_details.append(
					f"{slot.posting_date} at {slot.start_time} (Appointment: {slot.service_appointment})"
				)

			details_str = "<br>".join(appointment_details)
			if len(booked_slots) > 3:
				details_str += f"<br>...and {len(booked_slots) - 3} more"

			frappe.throw(
				_(
					"Cannot remove {0} from shift assignment. There are existing appointments booked on these days:<br><br>{1}<br><br>Please cancel these appointments first or keep these days in the shift assignment."
				).format(frappe.bold(removed_day_names), details_str),
				title=_("Cannot Remove Days with Bookings"),
			)

	def check_for_slot_regeneration(self):
		"""
		Check if changes require slot regeneration
		Returns: 'full', 'partial', or None
		"""
		if not hasattr(self.flags, "old_shift_type"):
			return None

		# Check if critical fields changed (requires full regeneration)
		if (
			self.flags.old_shift_type != self.shift_type
			or str(self.flags.old_start_date) != str(self.start_date)
			or str(self.flags.old_end_date) != str(self.end_date)
			or self.flags.old_repeat_type != self.repeat_type
		):
			return "full"

		# Check if only weekdays changed for Weekly repeat (partial regeneration)
		if self.repeat_type == "Weekly" and hasattr(self.flags, "old_days"):
			new_days = {d.weekday for d in self.days}
			if self.flags.old_days != new_days:
				return "partial"

		return None

	def handle_weekday_changes(self):
		"""Handle partial regeneration when only weekdays change"""
		old_days = self.flags.old_days
		new_days = {d.weekday for d in self.days}

		added_days = new_days - old_days
		removed_days = old_days - new_days

		if removed_days:
			# Delete slots for removed days (only unbooked ones)
			frappe.msgprint(
				_("Removing slots for {0}...").format(", ".join(sorted(removed_days))),
				indicator="blue",
				alert=True,
			)
			frappe.enqueue(
				"frappoint.frappoint.doctype.appointment_provider_slot.appointment_provider_slot.delete_slots_for_specific_days",
				shift_assignment=self.name,
				weekdays=list(removed_days),
				queue="default",
				timeout=300,
				is_async=True,
			)

		if added_days:
			# Generate slots for added days
			frappe.msgprint(
				_("Generating slots for {0}...").format(", ".join(sorted(added_days))),
				indicator="green",
				alert=True,
			)
			frappe.enqueue(
				"frappoint.frappoint.doctype.appointment_provider_slot.appointment_provider_slot.generate_slots_for_specific_days",
				shift_assignment=self.name,
				weekdays=list(added_days),
				queue="default",
				timeout=300,
				is_async=True,
			)

	def deactivate_slots(self):
		"""Mark all slots as unavailable when shift becomes inactive"""
		frappe.db.sql(
			"""
			UPDATE `tabAppointment Provider Slot`
			SET is_available = 0
			WHERE shift_assignment = %s
			AND service_appointment IS NULL
		""",
			self.name,
		)
		frappe.db.commit()
