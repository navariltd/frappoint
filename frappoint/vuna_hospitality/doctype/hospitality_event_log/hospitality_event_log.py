# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class HospitalityEventLog(Document):
	"""Append-only audit trail for hospitality records (design §23.3).

	Entries are written by `services.event_log.log_event`. Once inserted they cannot be edited or
	deleted, by anyone, through the document API.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		business_date: DF.Date | None
		data: DF.JSON | None
		event_type: DF.Data
		from_status: DF.Data | None
		naming_series: DF.Literal["HSP-LOG-.YYYY.-.########"]
		property: DF.Data | None
		reason: DF.SmallText | None
		reference_doctype: DF.Link
		reference_name: DF.DynamicLink
		request_id: DF.Data | None
		roles: DF.SmallText | None
		timestamp: DF.Datetime | None
		to_status: DF.Data | None
		user: DF.Link | None
	# end: auto-generated types

	def validate(self):
		if not self.is_new():
			frappe.throw(_("Hospitality Event Log entries cannot be changed."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Hospitality Event Log entries cannot be deleted."), frappe.PermissionError)
