# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

import random

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form


class ServiceProvider(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from frappoint.frappoint.doctype.service_provider_service.service_provider_service import ServiceProviderService

		active: DF.Check
		branch: DF.Link | None
		color_code: DF.Color | None
		company: DF.Link
		default_slot_length: DF.Int
		department: DF.Link | None
		designation: DF.Link | None
		email: DF.Data | None
		employee: DF.Link | None
		first_name: DF.Data
		gender: DF.Link | None
		google_calendar: DF.Link | None
		grade: DF.Link | None
		image: DF.AttachImage | None
		last_name: DF.Data | None
		middle_name_optional: DF.Data | None
		mobile_no: DF.Data | None
		provider_name: DF.Data | None
		services: DF.Table[ServiceProviderService]
		user: DF.Link | None
	# end: auto-generated types
	pass

	def validate(self):
		self.set_full_name()
		self.validate_user()
		self.validate_employee()
		self.assign_unique_color()
		# if not self.active:
		# self.ensure_no_upcoming_appointments()
		if not self.is_new():
			self.check_active_status_change()

	def on_trash(self):
		self.ensure_no_upcoming_appointments

	def ensure_no_upcoming_appointments(self):
		"""Checks if provider has upcoming appointments and blocks disable/delete."""
		upcoming = frappe.db.get_value(
			"Service Appointment",
			{
				"service_provider": self.name,
				"appointment_date": (">=", frappe.utils.today()),
				"status": ["!=", "Cancelled"],
				"docstatus": ["<", 2],
			},
			["name", "appointment_date", "start_time"],
			as_dict=True,
		)

		if upcoming:
			frappe.throw(
				_(
					"This provider has upcoming appointments, e.g. {0} on {1} at {2}. Cannot disable or delete."
				).format(upcoming.name, upcoming.appointment_date, upcoming.start_time),
				title=_("Active Appointments Found"),
			)

	@staticmethod
	def generate_random_color():
		min_val = 0x222222
		max_val = 0xDDDDDD
		return f"#{random.randint(min_val, max_val):06X}"

	def assign_unique_color(self):
		"""Generate a unique color code if empty."""
		if self.color_code:
			return

		existing_colors = {
			row.get("color_code")
			for row in frappe.get_all(
				"Service Provider", fields=["color_code"], filters={"color_code": ["!=", ""]}
			)
		}

		color = self.generate_random_color()
		attempts = 0

		while color in existing_colors:
			color = self.generate_random_color()
			attempts += 1
			if attempts > 20:
				color = f"#{random.getrandbits(24):06X}"
				break

		self.color_code = color

	def set_full_name(self):
		if self.last_name:
			self.provider_name = " ".join(filter(None, [self.first_name, self.last_name]))
		else:
			self.provider_name = self.first_name

	def validate_user(self):
		if self.user:
			if not frappe.db.exists("User", self.user):
				frappe.throw(_("User {0} does not exist").format(self.user))
			elif not frappe.db.exists("User", self.user, "enabled"):
				frappe.throw(_("User {0} is disabled").format(self.user))

			# check duplicate
			provider = frappe.db.exists("Service Provider", {"user": self.user, "name": ("!=", self.name)})
			if provider:
				frappe.throw(
					_("User <b>{0}</b> is already assigned to Service Provider {1}").format(
						self.user, get_link_to_form(self.doctype, provider)
					)
				)

	def validate_employee(self):
		if self.employee:
			if not frappe.db.exists("Employee", self.employee):
				frappe.throw(_("Employee {0} does not exist").format(self.employee))
			elif frappe.db.get_value("Employee", self.employee, "status") != "Active":
				frappe.throw(_("Employee {0} is not active").format(self.employee))

			# check duplicate
			provider = frappe.db.exists(
				"Service Provider", {"employee": self.employee, "name": ("!=", self.name)}
			)
			if provider:
				frappe.throw(
					_("Employee <b>{0}</b> is already assigned to Service Provider {1}").format(
						self.employee, get_link_to_form(self.doctype, provider)
					)
				)

	def check_active_status_change(self):
		"""Check if provider is being deactivated"""
		old_doc = self.get_doc_before_save()

		if old_doc and old_doc.active == 1 and self.active == 0:
			self.validate_deactivation()

	def validate_deactivation(self):
		"""
		When deactivating a provider:
		1. Check for future booked appointments
		2. Warn user about existing bookings
		3. Mark all future unbooked slots as unavailable
		"""
		# Check for future booked appointments
		today = frappe.utils.nowdate()

		future_bookings = frappe.db.sql(
			"""
			SELECT
				COUNT(*) as count,
				MIN(posting_date) as earliest_date,
				MAX(posting_date) as latest_date
			FROM `tabService Provider Appointment Slot`
			WHERE provider = %s
			AND service_appointment IS NOT NULL
			AND service_appointment != ''
			AND posting_date >= %s
		""",
			(self.name, today),
			as_dict=True,
		)

		if future_bookings and future_bookings[0].count > 0:
			booking_info = future_bookings[0]
			frappe.msgprint(
				_(
					"Warning: This provider has {0} future booked appointment(s) "
					"from {1} to {2}.<br><br>"
					"These appointments will remain valid, but no new bookings can be made."
				).format(booking_info.count, booking_info.earliest_date, booking_info.latest_date),
				indicator="orange",
				title=_("Future Bookings Exist"),
			)

	def on_update(self):
		"""Handle provider updates"""
		if not self.is_new():
			old_doc = self.get_doc_before_save()

			if old_doc and old_doc.active == 1 and self.active == 0:
				# Provider is being deactivated
				self.mark_future_slots_unavailable()
			elif old_doc and old_doc.active == 0 and self.active == 1:
				# Provider is being reactivated
				self.reactivate_future_slots()

	def mark_future_slots_unavailable(self):
		"""Mark all future unbooked slots as unavailable when provider is deactivated"""
		today = frappe.utils.nowdate()

		frappe.db.sql(
			"""
			UPDATE `tabService Provider Appointment Slot`
			SET is_available = 0
			WHERE provider = %s
			AND posting_date >= %s
			AND (service_appointment IS NULL OR service_appointment = '')
		""",
			(self.name, today),
		)

		frappe.msgprint(_("Marked future unbooked slots as unavailable"), indicator="blue", alert=True)

	def reactivate_future_slots(self):
		"""Reactivate future slots when provider is activated again"""
		today = frappe.utils.nowdate()

		# Get active shift assignments for this provider
		active_shifts = frappe.get_all(
			"Service Provider Shift Assignment",
			filters={"provider": self.name, "status": "Active", "docstatus": 1},
			pluck="name",
		)

		if active_shifts:
			# Reactivate slots belonging to active shift assignments
			frappe.db.sql(
				"""
				UPDATE `tabService Provider Appointment Slot`
				SET is_available = 1
				WHERE provider = %s
				AND posting_date >= %s
				AND shift_assignment IN %s
				AND (service_appointment IS NULL OR service_appointment = '')
			""",
				(self.name, today, active_shifts),
			)

			frappe.msgprint(
				_("Reactivated future slots for active shift assignments"), indicator="green", alert=True
			)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_practitioner_list(doctype, txt, searchfield, start, page_len, filters=None):
	active_filter = {"active": 1}

	filters = {**active_filter, **filters} if filters else active_filter

	fields = ["name", "provider_name", "mobile_no"]

	pattern = f"%{txt}%"

	text_in = {"name": ("like", pattern), "provider_name": ("like", pattern)}

	return frappe.get_all(
		"Service Provider",
		fields=fields,
		filters=filters,
		or_filters=text_in,
		start=start,
		page_length=page_len,
		order_by="name, provider_name",
		as_list=1,
	)
