# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, get_time, getdate, time_diff


class ServiceProviderShiftType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		break_end_time: DF.Time | None
		break_start_time: DF.Time | None
		end_time: DF.Time
		holiday_list: DF.Link | None
		start_time: DF.Time
	# end: auto-generated types
	pass

	def validate(self):
		start = get_time(self.start_time)
		end = get_time(self.end_time)
		self.validate_same_start_and_end(start, end)
		self.validate_circular_shift(start, end)

	def on_update(self):
		old_doc = self.get_doc_before_save()
		if not old_doc:
			return

		changed_fields = [
			"start_time",
			"end_time",
			"break_start_time",
			"break_end_time",
			"holiday_list",
		]

		if not any(str(old_doc.get(field)) != str(self.get(field)) for field in changed_fields):
			return

		from ...services.slot_cache_service import invalidate_provider_date_range_cache

		settings_horizon = int(
			frappe.db.get_single_value("Service Appointment Settings", "max_advance_days") or 30
		)
		for assignment in frappe.get_all(
			"Service Provider Shift Assignment",
			filters={"shift_type": self.name, "docstatus": 1},
			fields=["provider", "start_date", "end_date"],
		):
			end_date = assignment.end_date or add_days(getdate(), settings_horizon)
			invalidate_provider_date_range_cache(assignment.provider, assignment.start_date, end_date)

	def validate_same_start_and_end(self, start_time: datetime.time, end_time: datetime.time):
		if start_time == end_time:
			frappe.throw(
				title=_("Invalid Shift Times"),
				msg=_("Start time and end time cannot be same."),
			)

	def validate_circular_shift(self, start_time: datetime.time, end_time: datetime.time):
		shift_start, shift_end = self.get_shift_start_and_shift_end(start_time, end_time)
		if self.get_total_shift_duration_in_minutes(shift_start, shift_end) >= 1440:
			max_label = self.get_max_shift_buffer_label()
			frappe.throw(
				title=_("Invalid Shift Times"),
				msg=_("Please reduce {0} to avoid shift time overlapping with itself").format(
					frappe.bold(max_label)
				),
			)

	def get_total_shift_duration_in_minutes(
		self, shift_start: datetime.time, shift_end: datetime.time
	) -> int:
		return round(time_diff(shift_end, shift_start).total_seconds() / 60)

	def get_shift_start_and_shift_end(
		self, start_time: datetime.time, end_time: datetime.time
	) -> tuple[datetime]:
		shift_start = datetime.combine(getdate(), start_time)
		if start_time < end_time:
			shift_end = datetime.combine(getdate(), end_time)
		elif start_time > end_time:
			shift_end = datetime.combine(add_days(getdate(), 1), end_time)
		return shift_start, shift_end

	def get_assigned_providers(self, from_date: datetime.date) -> list[str]:
		filters = {"shift_type": self.name, "docstatus": "1", "status": "Active"}

		or_filters = [["end_date", ">=", from_date], ["end_date", "is", "not set"]]

		assigned_providers = frappe.get_all(
			"Service Provider Shift Assignment", filters=filters, or_filters=or_filters, pluck="provider"
		)

		# exclude inactive providers
		inactive_providers = frappe.db.get_all("Provider", {"active": 0}, pluck="name")

		return list(set(assigned_providers) - set(inactive_providers))

	def get_holiday_list(self, employee: str) -> str:
		# TODO: implement an erpnext installed guard here

		from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

		holiday_list_name = self.holiday_list or get_holiday_list_for_employee(employee, False)
		return holiday_list_name
