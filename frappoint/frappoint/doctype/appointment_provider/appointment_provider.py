# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AppointmentProvider(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		active: DF.Check
		color_code: DF.Color | None
		designation: DF.Link | None
		email: DF.Data | None
		employee: DF.Link | None
		first_name: DF.Data
		google_calendar: DF.Link | None
		grade: DF.Link | None
		last_name: DF.Data | None
		middle_name_optional: DF.Data | None
		mobile_no: DF.Data | None
		provider_name: DF.Data
		user: DF.Link | None
	# end: auto-generated types
	pass

	def validate(self):
		self.set_full_name()
		self.validate_user_id()

	def set_full_name(self):
		if self.last_name:
			self.provider_name = " ".join(filter(None, [self.first_name, self.last_name]))
		else:
			self.provider_name = self.first_name

	def validate_user_id(self):
		if not frappe.db.exists("User", self.user):
			frappe.throw(_("User {0} does not exist").format(self.user))
		elif not frappe.db.exists("User", self.user, "enabled"):
			frappe.throw(_("User {0} is disabled").format(self.user))

		# check duplicate
		provider = frappe.db.exists("Appointment Provider", {"user_id": self.user, "name": ("!=", self.name)})
		if provider:
			frappe.throw(
				_("User {0} is already assigned to Appointment Provider {1}").format(self.user, provider)
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
