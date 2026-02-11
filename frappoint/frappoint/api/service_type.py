import re

import frappe
from frappe import _

from ...payments import get_payment_gateways_for_service_type
from .service_provider import get_providers_for_service


@frappe.whitelist(allow_guest=True)
def get_service_types(
	company: str | None = None,
	active_only: bool = True,
	search_term: str | None = None,
	item_group: str | None = None,
	page: int = 1,
	page_size: int = 12,
) -> dict:
	"""
	Get all available service types with pagination
	Use case: Display services on booking page

	Args:
	        company: Filter by company
	        active_only: Only return active services (default: True)
	        search_term: Search in service name, appointment_type, item_name, short_description
	        item_group: Filter by item group/category
	        page: Page number (default: 1)
	        page_size: Number of items per page (default: 12)
	"""

	# Convert page and page_size to integers
	page = int(page) if page else 1
	page_size = int(page_size) if page_size else 12

	# Ensure page is at least 1
	if page < 1:
		page = 1

	filters = {}

	if company:
		filters["company"] = company

	if active_only:
		filters["disabled"] = 0

	if item_group:
		filters["item_group"] = item_group

	# Build or_filters for search functionality
	or_filters = None
	if search_term and search_term.strip():
		search_term = search_term.strip()
		or_filters = [
			["name", "like", f"%{search_term}%"],
			["appointment_type", "like", f"%{search_term}%"],
			["item_name", "like", f"%{search_term}%"],
			["short_description", "like", f"%{search_term}%"],
		]

	# Get total count for pagination metadata
	if or_filters:
		total_count = len(
			frappe.get_all(
				"Service Type",
				filters=filters,
				or_filters=or_filters,
				fields=["name"],
			)
		)
	else:
		total_count = frappe.db.count("Service Type", filters=filters)

	# Calculate pagination
	total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
	start = (page - 1) * page_size

	# Get paginated service types using database-level pagination
	service_types = frappe.get_list(
		"Service Type",
		filters=filters,
		or_filters=or_filters,
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
		start=start,
		page_length=page_size,
	)

	# Add price information to paginated results only
	for service in service_types:
		prices = frappe.get_all(
			"Service Type Price",
			filters={"parent": service.name, "duration": service.default_duration_in_minutes},
			fields=["price_name", "amount", "duration", "currency"],
			limit=1,
		)
		service["price"] = prices[0] if prices else None

	return {
		"data": service_types,
		"pagination": {
			"page": page,
			"page_size": page_size,
			"total_count": total_count,
			"total_pages": total_pages,
			"has_next": page < total_pages,
			"has_previous": page > 1,
		},
	}


@frappe.whitelist(allow_guest=True)
def get_service_type_details(service_type: str) -> dict:
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
			fields=["price_name", "amount", "duration", "currency"],
		),
		"providers": get_providers_for_service(service_type),
		"payment_gateways": get_payment_gateways_for_service_type(service_type),
	}
