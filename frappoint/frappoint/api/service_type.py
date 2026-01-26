import re

import frappe
from frappe import _

from ...payments import get_payment_gateways_for_service_type
from .service_provider import get_providers_for_service


@frappe.whitelist(allow_guest=True)
def get_service_types(company=None, active_only=True):
	"""
	Get all available service types
	Use case: Display services on booking page
	"""

	filters = {}

	if company:
		filters["company"] = company

	if active_only:
		filters["disabled"] = 0

	service_types = frappe.get_all(
		"Service Type",
		filters=filters,
		fields=[
			"name",
			"appointment_type",
			"short_description",
			"default_duration_in_minutes",
			"item_name",
			"item_group",
			"image",
		],
		order_by="appointment_type",
	)

	for service in service_types:
		prices = frappe.get_all(
			"Service Type Price",
			filters={"parent": service.name},
			fields=["price_name", "rate", "currency"],
			limit=1,
		)
		service["price"] = prices[0] if prices else None

	return service_types


@frappe.whitelist(allow_guest=True)
def get_service_type_details(service_type):
	"""
	Get detailed information about a specific service type
	Use case: Service detail page, booking form
	"""

	service = frappe.db.get_value(
		"Service Type",
		service_type,
		[
			"name",
			"appointment_type",
			"short_description",
			"image",
			"tags",
			"description",
			"default_duration_in_minutes",
		],
		as_dict=True,
	)

	if not service:
		frappe.throw("Service not found", frappe.DoesNotExistError)

	return {
		**service,
		"tags": [t.strip() for t in re.split(r"[,\n]+", service.tags or "") if t.strip()],
		"prices": frappe.db.get_all(
			"Service Type Price",
			filters={"parent": service_type},
			fields=["price_name", "rate", "currency"],
		),
		"providers": get_providers_for_service(service_type),
		"payment_gateways": get_payment_gateways_for_service_type(service_type),
	}
