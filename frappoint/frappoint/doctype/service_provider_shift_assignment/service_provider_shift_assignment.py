# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_link_to_form, nowdate

from ..service_provider_appointment_slot.service_provider_appointment_slot import (
	generate_for_shift,
	service_type_requires_service_unit,
)


class MultipleShiftError(frappe.ValidationError):
	pass


class OverlappingShiftError(frappe.ValidationError):
	pass


class ServiceProviderShiftAssignment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		company: DF.Link
		end_date: DF.Date | None
		friday: DF.Check
		monday: DF.Check
		provider: DF.Link
		provider_name: DF.Data | None
		repeat_type: DF.Literal["Daily", "Weekly"]
		saturday: DF.Check
		service_unit: DF.Link | None
		shift_type: DF.Link
		start_date: DF.Date
		status: DF.Literal["Active", "Inactive"]
		sunday: DF.Check
		thursday: DF.Check
		tuesday: DF.Check
		wednesday: DF.Check
	# end: auto-generated types

	def validate(self):
		self.validate_active_provider()
		if self.end_date:
			self.validate_from_to_dates("start_date", "end_date")
		self.validate_overlapping_shifts()
		self.validate_shift_service_unit()
		self.validate_provider_can_handle_service_units()

	def before_update_after_submit(self):
		"""Store old values and validate before update"""
		if not self.is_new() and self.docstatus == 1:
			old_doc = frappe.get_doc("Service Provider Shift Assignment", self.name)

			self.flags.old_shift_type = old_doc.shift_type
			self.flags.old_start_date = old_doc.start_date
			self.flags.old_end_date = old_doc.end_date
			self.flags.old_repeat_type = old_doc.repeat_type
			self.flags.old_status = old_doc.status

			if old_doc.repeat_type == "Weekly":
				day_fields = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
				DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
				self.flags.old_days = {
					DAYS[idx] for idx, field in enumerate(day_fields) if old_doc.get(field)
				}

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
			self.reactivate_slots()
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
				"frappoint.frappoint.doctype.service_provider_appointment_slot.service_provider_appointment_slot.generate_for_shift",
				shift_assignment=self.name,
				queue="default",
				timeout=300,
				is_async=True,
			)
		elif regeneration_type == "partial":
			# Partial regeneration (only weekdays changed)
			self.handle_weekday_changes()

	def on_cancel(self):
		self.handle_slot_cleanup_on_cancel()

	def validate_active_provider(self):
		if self.provider and frappe.db.get_value("Service Provider", self.provider, "active") == 0:
			frappe.throw(
				_("Transactions cannot be created for an Inactive Service Provider {0}.").format(
					get_link_to_form("Service Provider", self.provider)
				),
			)

	def validate_overlapping_shifts(self):
		"""
		Allow multiple shifts for same provider on same day
		if they're in different service units and overlapping times
		"""
		if self.status == "Inactive":
			return

		overlapping_dates = self.get_overlapping_dates()

		for d in overlapping_dates:
			if not self.has_overlapping_timings(self.shift_type, d.shift_type):
				continue

			other_shift = frappe.get_doc("Service Provider Shift Assignment", d.name)

			# Both service units exist
			if self.service_unit and other_shift.service_unit:
				# Different units -> allowed with warning
				if self.service_unit != other_shift.service_unit:
					frappe.msgprint(
						_(
							"Warning: Provider {0} has overlapping shifts in different locations. "
							"Ensure they can physically be in both places."
						).format(frappe.bold(self.provider)),
						indicator="orange",
						alert=True,
					)
					continue

			# Same unit OR missing unit -> conflict
			self.throw_overlap_error(d)

	def throw_overlap_error(self, shift_details):
		shift_details = frappe._dict(shift_details)
		if shift_details.docstatus == 1 and shift_details.status == "Active":
			msg = _(
				"Provider {0} already has an active Shift {1}: {2} that overlaps within this period."
			).format(
				frappe.bold(self.provider),
				frappe.bold(shift_details.shift_type),
				get_link_to_form("Service Provider Shift Assignment", shift_details.name),
			)
			frappe.throw(msg, title=_("Overlapping Shifts"), exc=OverlappingShiftError)

	def validate_provider_can_handle_service_units(self):
		"""
		Validate that provider's services match the assigned service unit
		"""
		if not self.service_unit:
			return

		# Get service unit type
		service_unit_doc = frappe.get_doc("Service Unit", self.service_unit)
		service_unit_type = service_unit_doc.unit_type

		# Get all services this provider offers
		provider_services = frappe.get_all(
			"Service Provider Service", filters={"parent": self.provider, "disabled": 0}, pluck="service_type"
		)

		# Check if ANY of their services can use this unit type
		can_use_unit = False
		for service_type in provider_services:
			service_doc = frappe.get_doc("Service Type", service_type)

			# Check if this service requires this unit type
			for unit_type_row in service_doc.service_unit_types:
				if unit_type_row.service_unit_type == service_unit_type:
					can_use_unit = True
					break

			if can_use_unit:
				break

		if not can_use_unit:
			# Get list of services that DO require this unit type
			compatible_services = []
			all_services = frappe.get_all("Service Type", filters={"disabled": 0}, pluck="name")

			for service in all_services:
				service_doc = frappe.get_doc("Service Type", service)
				for unit_type_row in service_doc.service_unit_types:
					if unit_type_row.service_unit_type == service_unit_type:
						compatible_services.append(service)
						break

			frappe.msgprint(
				_(
					"Notice: Provider {0} doesn't offer services that use {1} ({2}). "
					"Compatible services include: {3}"
				).format(
					frappe.bold(self.provider),
					frappe.bold(self.service_unit),
					service_unit_type,
					", ".join(compatible_services[:5]) if compatible_services else "None",
				),
				indicator="orange",
				alert=True,
			)

	def get_overlapping_dates(self):
		if not self.name:
			self.name = "New Provider Shift Assignment"

		shift = frappe.qb.DocType("Service Provider Shift Assignment")
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

		s1 = frappe.db.get_value(
			"Service Provider Shift Type", shift_1, ["start_time", "end_time"], as_dict=True
		)
		s2 = frappe.db.get_value(
			"Service Provider Shift Type", shift_2, ["start_time", "end_time"], as_dict=True
		)

		for d in [s1, s2]:
			if d.end_time <= d.start_time:
				d.end_time += timedelta(days=1)

		return s1.end_time > s2.start_time and s1.start_time < s2.end_time

	def validate_weekday_changes(self, old_doc):
		"""Validate that removed weekdays don't have booked appointments"""
		if self.repeat_type != "Weekly" or old_doc.repeat_type != "Weekly":
			return

		# Map weekday names to indices
		day_fields = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
		DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

		old_days = {DAYS[idx] for idx, field in enumerate(day_fields) if old_doc.get(field)}
		new_days = {DAYS[idx] for idx, field in enumerate(day_fields) if self.get(field)}
		removed_days = old_days - new_days

		if not removed_days:
			return

		removed_indices = [(DAYS.index(day) + 1) % 7 + 1 for day in removed_days]

		# Check if any booked appointments exist on removed days
		booked_slots = frappe.db.sql(
			"""
			SELECT
				posting_date,
				start_time,
				end_time,
				service_appointment
			FROM `tabService Provider Appointment Slot`
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

	def validate_shift_service_unit(self):
		"""
		Validate shift assignment based on provider's services
		Called from Service Provider Shift Assignment's validate
		"""
		if not self.service_unit:
			# Check if any of the provider's services require a service unit
			provider_services = frappe.get_all(
				"Service Provider Service",
				filters={"parent": self.provider, "disabled": 0},
				pluck="service_type",
			)

			requires_unit = False
			for service_type in provider_services:
				req, _unit_types = service_type_requires_service_unit(service_type)
				if req:
					requires_unit = True
					break

			if requires_unit:
				frappe.throw(
					_(
						"Warning: This provider offers services that require a service unit, "
						"but no service unit is assigned to this shift. "
						"Appointments requiring service units will not be available during this shift."
					),
					title=_("Missing Service Unit"),
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
			day_fields = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
			DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
			new_days = {DAYS[idx] for idx, field in enumerate(day_fields) if self.get(field)}

			if self.flags.old_days != new_days:
				return "partial"

		return None

	def handle_weekday_changes(self):
		"""Handle partial regeneration when only weekdays change"""
		old_days = self.flags.old_days

		day_fields = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
		DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
		new_days = {DAYS[idx] for idx, field in enumerate(day_fields) if self.get(field)}

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
				"frappoint.frappoint.doctype.service_provider_appointment_slot.service_provider_appointment_slot.delete_slots_for_specific_days",
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
				"frappoint.frappoint.doctype.service_provider_appointment_slot.service_provider_appointment_slot.generate_slots_for_specific_days",
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
			UPDATE `tabService Provider Appointment Slot`
			SET is_available = 0
			WHERE shift_assignment = %s
			AND service_appointment IS NULL
		""",
			self.name,
		)

	def reactivate_slots(self):
		"""Mark all unbooked future slots as available when shift is reactivated"""
		today = nowdate()

		slot_count = frappe.db.count(
			"Service Provider Appointment Slot",
			{"shift_assignment": self.name, "posting_date": [">=", today]},
		)

		if slot_count == 0:
			# No slots exist, need to generate them
			frappe.msgprint(
				_("No existing slots found. Generating new slots..."), indicator="blue", alert=True
			)
			generate_for_shift(self.name)
			return

		frappe.db.sql(
			"""
			UPDATE `tabService Provider Appointment Slot`
			SET is_available = 1
			WHERE shift_assignment = %s
			AND posting_date >= %s
			AND (service_appointment IS NULL OR service_appointment = '')
			""",
			(self.name, today),
		)

	def handle_slot_cleanup_on_cancel(self):
		"""
		When a shift assignment is cancelled:
		1. Check for any booked appointments
		2. If booked appointments exist, prevent cancellation
		3. If no bookings, delete all associated slots
		"""
		# Check for booked slots
		booked_slots = frappe.db.sql(
			"""
			SELECT
				COUNT(*) as count,
				GROUP_CONCAT(DISTINCT service_appointment) as appointments
			FROM `tabService Provider Appointment Slot`
			WHERE shift_assignment = %s
			AND service_appointment IS NOT NULL
			AND service_appointment != ''
		""",
			self.name,
			as_dict=True,
		)

		if booked_slots and booked_slots[0].count > 0:
			appointments = booked_slots[0].appointments.split(",")
			frappe.throw(
				_(
					"Cannot cancel shift assignment. There are {0} booked appointment(s): {1}.<br><br>"
					"Please cancel or reschedule these appointments first."
				).format(
					booked_slots[0].count,
					", ".join(appointments[:5]),  # Show first 5
				),
				title=_("Cannot Cancel - Active Bookings Exist"),
			)

		# Delete all slots for this shift assignment
		deleted_count = frappe.db.sql(
			"""
			DELETE FROM `tabService Provider Appointment Slot`
			WHERE shift_assignment = %s
		""",
			self.name,
		)

		frappe.db.commit()

		frappe.msgprint(
			_("Deleted {0} appointment slots for this shift assignment").format(
				deleted_count if isinstance(deleted_count, int) else "all"
			),
			indicator="blue",
			alert=True,
		)
