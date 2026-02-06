# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from datetime import date
from typing import ClassVar

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form, getdate, today


class ServiceProviderShiftAssignmentTool(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappoint.frappoint.doctype.service_provider_shift_assignment_tool_detail.service_provider_shift_assignment_tool_detail import (
			ServiceProviderShiftAssignmentToolDetail,
		)

		action: DF.Literal["Assign Shift"]
		branch: DF.Link | None
		company: DF.Link
		department: DF.Link | None
		designation: DF.Link | None
		end_date: DF.Date | None
		grade: DF.Link | None
		provider_shift_type: DF.Link | None
		providers: DF.Table[ServiceProviderShiftAssignmentToolDetail]
		service_unit: DF.Link | None
		service_unit_type: DF.Link | None
		start_date: DF.Date | None
		status: DF.Literal["Active", "Inactive"]
	# end: auto-generated types

	_table_fieldnames: ClassVar[list] = []

	def db_insert(self, *args, **kwargs):
		pass

	def load_from_db(self):
		"""Override to prevent database loading for this tool."""
		# Set required attributes for a single doctype
		self.name = "Service Provider Shift Assignment Tool"
		self._original_modified = frappe.utils.now()
		self.modified = self._original_modified

	def db_update(self):
		pass

	def delete(self):
		pass

	@staticmethod
	def get_list(filters=None, **kwargs):
		pass

	@staticmethod
	def get_count(filters=None, **kwargs):
		pass

	@staticmethod
	def get_stats(filters=None, **kwargs):
		pass

	def check_if_latest(self):
		"""Override to skip version checking for this tool."""
		if not hasattr(self, "_action"):
			self._action = "save"

	@frappe.whitelist()
	def get_providers(self):
		"""
		Fetch service providers based on quick filters and advanced filters.
		Returns list of providers eligible for shift assignment.
		"""
		if not self.company:
			frappe.throw(_("Please select a Company to fetch providers."))

		# Build filters from quick filter fields
		quick_filter_fields = [
			"company",
			"branch",
			"department",
			"designation",
			"grade",
		]
		filters = [[d, "=", self.get(d)] for d in quick_filter_fields if self.get(d)]

		ServiceProvider = frappe.qb.DocType("Service Provider")
		ShiftAssignment = frappe.qb.DocType("Service Provider Shift Assignment")

		query = frappe.qb.get_query(
			ServiceProvider,
			fields=[
				ServiceProvider.name.as_("service_provider"),
				ServiceProvider.provider_name,
				ServiceProvider.branch,
				ServiceProvider.department,
			],
			filters=filters,
		).where(ServiceProvider.active == 1)

		# Exclude providers with existing active shift assignments for the date range
		if self.status == "Active" and self.provider_shift_type and self.start_date:
			active_shift_subquery = (
				frappe.qb.from_(ShiftAssignment)
				.select(ShiftAssignment.provider)
				.where(
					(ShiftAssignment.shift_type == self.provider_shift_type)
					& (ShiftAssignment.status == "Active")
					& (ShiftAssignment.docstatus == 1)
					& ((ShiftAssignment.end_date >= self.start_date) | (ShiftAssignment.end_date.isnull()))
				)
			)

			query = query.where(ServiceProvider.name.notin(active_shift_subquery))

			if self.end_date:
				end_date_subquery = (
					frappe.qb.from_(ShiftAssignment)
					.select(ShiftAssignment.provider)
					.where(ShiftAssignment.start_date <= self.end_date)
				)

				query = query.where(ServiceProvider.name.notin(end_date_subquery))
		print(query.run(as_dict=True))
		return query.run(as_dict=True)

	@frappe.whitelist()
	def bulk_assign_shifts(self):
		"""
		Assign or deactivate shifts for service providers based on status.
		If status is 'Active': Create new Service Provider Shift Assignments
		If status is 'Inactive': Deactivate existing Service Provider Shift Assignments
		"""
		if not self.providers:
			frappe.throw(_("Please select at least one Service Provider to assign shifts."))

		if not self.provider_shift_type:
			frappe.throw(_("Please select a Service Provider Shift Type."))

		if not self.start_date:
			frappe.throw(_("Please select a Start Date."))

		if not self.company:
			frappe.throw(_("Please select a Company."))

		success, failure = [], []

		for row in self.providers:
			try:
				frappe.db.savepoint("before_shift_assignment")

				if self.status == "Active":
					# Create a new shift assignment
					assignment = self._create_shift_assignment(
						row.service_provider,
						self.company,
						self.provider_shift_type,
						self.start_date,
						self.end_date,
						self.status,
						row.service_unit,
					)
					success.append(
						{
							"doc": get_link_to_form("Service Provider Shift Assignment", assignment.name),
							"provider": row.service_provider,
						}
					)
				elif self.status == "Inactive":
					# Deactivate existing shift assignments
					self._deactivate_shift_assignment(
						row.service_provider,
						self.provider_shift_type,
						self.start_date,
						self.end_date,
					)
					success.append(
						{
							"doc": row.service_provider,
							"provider": row.service_provider_name,
							"action": "deactivated",
						}
					)

			except Exception as e:
				frappe.db.rollback(save_point="before_shift_assignment")
				frappe.log_error(
					f"Shift Assignment failed for provider {row.service_provider}",
					f"Shift Assignment failed for provider {row.service_provider}: {e}",
					reference_doctype="Service Provider Shift Assignment",
				)
				failure.append(
					{
						"provider": row.service_provider_name,
						"error": str(e),
					}
				)

		frappe.clear_messages()

		# Show summary message
		if success:
			frappe.msgprint(
				_("{0} shift assignment(s) processed successfully. {1} failed.").format(
					len(success), len(failure)
				),
				alert=True,
				indicator="green" if not failure else "yellow",
			)

		return {
			"success": success,
			"failure": failure,
		}

	def _create_shift_assignment(
		self,
		service_provider: str,
		company: str,
		provider_shift_type: str,
		start_date: str,
		end_date: str | None,
		status: str,
		service_unit: str | None = None,
	):
		"""Create a new Service Provider Shift Assignment document."""
		assignment = frappe.new_doc("Service Provider Shift Assignment")
		assignment.provider = service_provider
		assignment.company = company
		assignment.shift_type = provider_shift_type
		assignment.start_date = start_date
		assignment.end_date = end_date
		assignment.status = status
		if service_unit:
			assignment.service_unit = service_unit
		assignment.save()
		assignment.submit()
		return assignment

	def _deactivate_shift_assignment(
		self,
		service_provider: str,
		provider_shift_type: str,
		start_date: str,
		end_date: str | None,
	):
		"""Deactivate existing shift assignments for the provider."""
		filters = {
			"provider": service_provider,
			"shift_type": provider_shift_type,
			"status": "Active",
			"docstatus": 1,
		}

		assignments = frappe.get_list(
			"Service Provider Shift Assignment",
			filters=filters,
			fields=["name"],
		)

		for assignment_doc in assignments:
			doc = frappe.get_doc("Service Provider Shift Assignment", assignment_doc.name)
			# Check if assignment overlaps with the specified date range
			if self._has_date_overlap(doc.start_date, doc.end_date, start_date, end_date):
				doc.status = "Inactive"
				doc.save()

	def _normalize_date(self, value):
		if not value:
			return None
		return getdate(value)

	def _has_date_overlap(self, existing_start, existing_end, new_start, new_end) -> bool:
		"""Check if two date ranges overlap."""
		# Convert all dates to date objects
		existing_start = self._normalize_date(existing_start)
		new_start = self._normalize_date(new_start)

		if not existing_start or not new_start:
			return True

		new_end = self._normalize_date(new_end) or date.max
		existing_end = self._normalize_date(existing_end) or date.max

		# Check if ranges overlap
		return not (existing_end < new_start or new_end < existing_start)
