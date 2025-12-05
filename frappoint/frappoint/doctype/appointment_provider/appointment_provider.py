# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

import random

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form


class AppointmentProvider(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		active: DF.Check
		color_code: DF.Color | None
		default_slot_length: DF.Int
		designation: DF.Link | None
		email: DF.Data | None
		employee: DF.Link | None
		first_name: DF.Data
		google_calendar: DF.Link | None
		grade: DF.Link | None
		last_name: DF.Data | None
		middle_name_optional: DF.Data | None
		mobile_no: DF.Data | None
		provider_name: DF.Data | None
		user: DF.Link | None
	# end: auto-generated types
	pass

	def validate(self):
		self.set_full_name()
		self.validate_user()
		self.validate_employee()
		self.assign_unique_color()
		if not self.active:
			self.ensure_no_upcoming_appointments()

	def on_trash(self):
		self.ensure_no_upcoming_appointments

	def ensure_no_upcoming_appointments(self):
		"""Checks if provider has upcoming appointments and blocks disable/delete."""
		upcoming = frappe.db.get_value(
			"Service Appointment",
			{
				"appointment_provider": self.name,
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
				"Appointment Provider", fields=["color_code"], filters={"color_code": ["!=", ""]}
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
			provider = frappe.db.exists(
				"Appointment Provider", {"user": self.user, "name": ("!=", self.name)}
			)
			if provider:
				frappe.throw(
					_("User <b>{0}</b> is already assigned to Appointment Provider {1}").format(
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
				"Appointment Provider", {"employee": self.employee, "name": ("!=", self.name)}
			)
			if provider:
				frappe.throw(
					_("Employee <b>{0}</b> is already assigned to Appointment Provider {1}").format(
						self.employee, get_link_to_form(self.doctype, provider)
					)
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
		"Appointment Provider",
		fields=fields,
		filters=filters,
		or_filters=text_in,
		start=start,
		page_length=page_len,
		order_by="name, provider_name",
		as_list=1,
	)
