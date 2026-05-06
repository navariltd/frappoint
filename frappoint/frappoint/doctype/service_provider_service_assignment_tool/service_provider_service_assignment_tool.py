# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from typing import ClassVar

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form


class ServiceProviderServiceAssignmentTool(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappoint.frappoint.doctype.service_provider_service_assignment_provider_detail.service_provider_service_assignment_provider_detail import (
			ServiceProviderServiceAssignmentProviderDetail,
		)
		from frappoint.frappoint.doctype.service_provider_service_assignment_service_detail.service_provider_service_assignment_service_detail import (
			ServiceProviderServiceAssignmentServiceDetail,
		)

		action: DF.Literal["Assign Service to Providers", "Assign Services to Provider"]
		branch: DF.Link | None
		company: DF.Link
		department: DF.Link | None
		designation: DF.Link | None
		grade: DF.Link | None
		providers: DF.Table[ServiceProviderServiceAssignmentProviderDetail]
		service_provider: DF.Link | None
		service_type: DF.Link | None
		services: DF.Table[ServiceProviderServiceAssignmentServiceDetail]
		status: DF.Literal["Active", "Inactive"]
	# end: auto-generated types

	_table_fieldnames: ClassVar[list] = []

	def save(self):
		pass

	def db_insert(self, *args, **kwargs):
		pass

	def load_from_db(self):
		pass

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
		pass

	@frappe.whitelist()
	def get_providers(self):
		"""Fetch service providers based on filters."""
		if not self.company:
			frappe.throw(_("Please select a Company to fetch providers."))

		quick_filter_fields = [
			"company",
			"branch",
			"department",
			"designation",
			"grade",
		]
		filters = [[d, "=", self.get(d)] for d in quick_filter_fields if self.get(d)]

		ServiceProvider = frappe.qb.DocType("Service Provider")
		ProviderService = frappe.qb.DocType("Service Provider Service")

		query = frappe.qb.get_query(
			ServiceProvider,
			fields=[
				ServiceProvider.name.as_("service_provider"),
				ServiceProvider.provider_name,
			],
			filters=filters,
		).where(ServiceProvider.active == 1)

		# Exclude providers who already have this service assigned (if status is Active)
		if self.status == "Active" and self.service_type and self.action == "Assign Service to Providers":
			query = query.where(
				ServiceProvider.name.notin(
					frappe.qb.from_(ProviderService)
					.select(ProviderService.parent)
					.where(
						(ProviderService.service_type == self.service_type)
						& (ProviderService.parenttype == "Service Provider")
					)
				)
			)

		elif self.status == "Inactive" and self.service_type:
			query = query.where(
				ServiceProvider.name.isin(
					frappe.qb.from_(ProviderService)
					.select(ProviderService.parent)
					.where(
						(ProviderService.service_type == self.service_type)
						& (ProviderService.parenttype == "Service Provider")
					)
				)
			)

		return query.run(as_dict=True)

	@frappe.whitelist()
	def get_services(self):
		"""Fetch service types available for assignment."""
		if not self.company:
			frappe.throw(_("Please select a Company to fetch services."))

		ServiceType = frappe.qb.DocType("Service Type")
		ProviderService = frappe.qb.DocType("Service Provider Service")

		query = frappe.qb.get_query(
			ServiceType,
			fields=[
				ServiceType.name.as_("service_type"),
			],
		).where(ServiceType.disabled == 0)

		# Exclude services already assigned to this provider (if status is Active)
		if self.action == "Assign Services to Provider" and self.service_provider:
			if self.status == "Active":
				query = query.where(
					ServiceType.name.notin(
						frappe.qb.from_(ProviderService)
						.select(ProviderService.service_type)
						.where(
							(ProviderService.parent == self.service_provider)
							& (ProviderService.parenttype == "Service Provider")
						)
					)
				)

			elif self.status == "Inactive":
				query = query.where(
					ServiceType.name.isin(
						frappe.qb.from_(ProviderService)
						.select(ProviderService.service_type)
						.where(
							(ProviderService.parent == self.service_provider)
							& (ProviderService.parenttype == "Service Provider")
						)
					)
				)

		return query.run(as_dict=True)

	@frappe.whitelist()
	def bulk_assign_services(self):
		"""Assign or remove services to/from providers."""
		if self.action == "Assign Service to Providers":
			return self._assign_service_to_providers()
		elif self.action == "Assign Services to Provider":
			return self._assign_services_to_provider()

	def _assign_service_to_providers(self):
		"""Assign one service to multiple providers."""
		if not self.providers:
			frappe.throw(_("Please select at least one Service Provider."))
		if not self.service_type:
			frappe.throw(_("Please select a Service Type."))
		if not self.company:
			frappe.throw(_("Please select a Company."))

		success, failure = [], []

		for row in self.providers:
			try:
				# Check if provider is active
				provider_active = frappe.db.get_value(
					"Service Provider", row.get("service_provider"), "active"
				)
				if not provider_active:
					raise frappe.ValidationError(
						_("Service Provider {0} is not active").format(row.get("service_provider"))
					)

				frappe.db.savepoint("before_service_assignment")

				if self.status == "Active":
					if not self.service_type:
						raise frappe.ValidationError(_("Service Type is required"))

					self._add_service_to_provider(row.get("service_provider"), self.service_type)
					success.append({"provider": row.get("service_provider"), "action": "assigned"})
				elif self.status == "Inactive":
					if not self.service_type:
						raise frappe.ValidationError(_("Service Type is required"))

					self._remove_service_from_provider(row.get("service_provider"), self.service_type)
					success.append({"provider": row.get("service_provider"), "action": "removed"})

			except Exception as e:
				frappe.db.rollback(save_point="before_service_assignment")
				frappe.log_error(
					f"Service assignment failed for provider {row.get('service_provider')}",
					f"Service assignment failed for provider {row.get('service_provider')}: {e}",
					reference_doctype="Service Provider Service",
				)
				failure.append({"provider": row.get("service_provider"), "error": str(e)})

		frappe.clear_messages()
		if success:
			frappe.msgprint(
				_("{0} service assignment(s) processed successfully. {1} failed.").format(
					len(success), len(failure)
				),
				alert=True,
				indicator="green" if not failure else "yellow",
			)

		return {"success": success, "failure": failure}

	def _assign_services_to_provider(self):
		"""Assign multiple services to one provider."""
		if not self.services:
			frappe.throw(_("Please select at least one Service Type."))
		if not self.service_provider:
			frappe.throw(_("Please select a Service Provider."))
		if not self.company:
			frappe.throw(_("Please select a Company."))

		# Check if provider is active
		provider_active = frappe.db.get_value("Service Provider", self.service_provider, "active")
		if not provider_active:
			frappe.throw(_("Service Provider {0} is not active").format(self.service_provider))

		success, failure = [], []

		for row in self.services:
			try:
				frappe.db.savepoint("before_service_assignment")

				if self.status == "Active":
					self._add_service_to_provider(self.service_provider, row.service_type)
					success.append({"service_type": row.service_type, "action": "assigned"})
				elif self.status == "Inactive":
					self._remove_service_from_provider(self.service_provider, row.service_type)
					success.append({"service_type": row.service_type, "action": "removed"})

			except Exception as e:
				frappe.db.rollback(save_point="before_service_assignment")
				frappe.log_error(
					f"Service assignment failed for service {row.service_type}",
					f"Service assignment failed for service {row.service_type}: {e}",
					reference_doctype="Service Provider Service",
				)
				failure.append({"service_type": row.service_type, "error": str(e)})

		frappe.clear_messages()
		if success:
			frappe.msgprint(
				_("{0} service assignment(s) processed successfully. {1} failed.").format(
					len(success), len(failure)
				),
				alert=True,
				indicator="green" if not failure else "yellow",
			)

		return {"success": success, "failure": failure}

	def _add_service_to_provider(self, provider: str, service: str):
		"""Add a service to a provider's Service Provider Service child table."""
		provider_doc = frappe.get_doc("Service Provider", provider)

		# Check if service already exists
		existing = any(d.service_type == service for d in provider_doc.services)
		if existing:
			frappe.throw(_("Service {0} is already assigned to {1}").format(service, provider))

		# Add service to child table
		provider_doc.append("services", {"service_type": service})
		provider_doc.save()

	def _remove_service_from_provider(self, provider: str, service: str):
		"""Remove a service from a provider's Service Provider Service child table."""
		provider_doc = frappe.get_doc("Service Provider", provider)

		# Find and remove the service
		services_to_remove = [d for d in provider_doc.services if d.service_type == service]
		if not services_to_remove:
			frappe.throw(_("Service {0} is not assigned to {1}").format(service, provider))

		for service_row in services_to_remove:
			provider_doc.remove(service_row)

		provider_doc.save()
