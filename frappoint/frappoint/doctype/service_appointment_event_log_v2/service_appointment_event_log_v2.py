# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

if TYPE_CHECKING:
	from frappe.types import DF


class ServiceAppointmentEventLogV2(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		appointment: DF.Link
		changed_at: DF.Datetime | None
		changed_by: DF.Link | None
		event_type: DF.Literal[
			"Status Changed",
			"Provider Changed",
			"Provider Handover",
			"Unit Changed",
			"Paused",
			"Resumed",
			"Cancelled",
			"Rescheduled",
		]
		naming_series: DF.Literal["SA-ELOG-.YYYY.-.#####"]
		new_value: DF.JSON | None
		notes: DF.Text | None
		old_value: DF.JSON | None
	# end: auto-generated types

	def validate(self):
		"""Validate event log record."""
		# Validate appointment exists
		if not frappe.db.exists("Service Appointment", self.appointment):
			frappe.throw(_("Service Appointment {0} does not exist").format(self.appointment))

	def before_insert(self):
		"""Before insert operations."""
		# Auto-set changed_by and changed_at if not provided
		if not self.changed_by:
			self.changed_by = frappe.session.user
		if not self.changed_at:
			self.changed_at = now_datetime()

	@staticmethod
	def log_event(
		appointment_id: str,
		event_type: str,
		old_value=None,
		new_value=None,
		notes: str | None = None,
	) -> "ServiceAppointmentEventLogV2":
		"""Create and save an event log entry."""
		event_log = frappe.new_doc("Service Appointment Event Log V2")
		event_log.appointment = appointment_id
		event_log.event_type = event_type
		event_log.old_value = old_value
		event_log.new_value = new_value
		event_log.notes = notes
		event_log.changed_by = frappe.session.user
		event_log.changed_at = now_datetime()
		event_log.insert(ignore_permissions=True)
		return event_log
