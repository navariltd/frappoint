import re

import frappe
from frappe import _

from ...payments import get_payment_gateways_for_service_type
from .service_provider import get_providers_for_service


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_service_types(
	company: str | None = None,
	active_only: bool = True,
	search_term: str | None = None,
	item_group: str | None = None,
	page: int = 1,
	page_size: int = 12,
	sort_by=None,
	min_price=None,
	max_price=None,
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
	        sort_by: Sort order (name_asc, name_desc, price_asc, price_desc, duration_asc, duration_desc)
	        min_price: Minimum price filter
	        max_price: Maximum price filter
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

	# Determine sort order
	order_by = "appointment_type"  # default
	if sort_by == "name_asc":
		order_by = "appointment_type asc"
	elif sort_by == "name_desc":
		order_by = "appointment_type desc"
	elif sort_by == "duration_asc":
		order_by = "default_duration_in_minutes asc"
	elif sort_by == "duration_desc":
		order_by = "default_duration_in_minutes desc"
	# Note: price sorting will be done after fetching since price is in child table

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
		order_by=order_by,
		start=start,
		page_length=page_size,
		ignore_permissions=True,
	)

	# Add price information to paginated results only
	for service in service_types:
		prices = frappe.get_all(
			"Service Type Price",
			filters={
				"parent": service.name,
				"duration": service.default_duration_in_minutes,
			},
			fields=["price_name", "amount", "duration", "currency"],
			limit=1,
		)
		service["price"] = prices[0] if prices else None

	# Filter by price range if specified
	if min_price is not None or max_price is not None:
		min_price = float(min_price) if min_price else 0
		max_price = float(max_price) if max_price else float("inf")

		service_types = [
			service
			for service in service_types
			if service.get("price") and min_price <= service["price"].get("amount", 0) <= max_price
		]

	# Sort by price if requested (must be done after fetching prices)
	if sort_by == "price_asc":
		service_types.sort(key=lambda x: x.get("price", {}).get("amount", 0) if x.get("price") else 0)
	elif sort_by == "price_desc":
		service_types.sort(
			key=lambda x: x.get("price", {}).get("amount", 0) if x.get("price") else 0,
			reverse=True,
		)

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


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_price_range(company: str | None = None, item_group: str | None = None) -> dict:
	"""
	Get the minimum and maximum price across all service types
	Use case: Set slider limits for price range filter

	Args:
	        company: Filter by company
	        item_group: Filter by item group/category
	"""
	filters: dict[str, int | str | list] = {"parenttype": "Service Type"}

	if company or item_group:
		service_type_filters: dict[str, int | str] = {"disabled": 0}
		if company:
			service_type_filters["company"] = company
		if item_group:
			service_type_filters["item_group"] = item_group

		service_types = frappe.get_all(
			"Service Type", filters=service_type_filters, fields=["name"], pluck="name"
		)

		if not service_types:
			return {"min_price": 0, "max_price": 0, "currency": "USD"}

		filters["parent"] = ["in", service_types]

	prices = frappe.get_all(
		"Service Type Price",
		filters=filters,
		fields=["amount", "currency"],
		order_by="amount",
	)

	if not prices:
		return {"min_price": 0, "max_price": 1000, "currency": "USD"}

	min_price = min(p.amount for p in prices)
	max_price = max(p.amount for p in prices)

	# Get the most common currency (in case there are multiple)
	currency = max(
		set(p.currency for p in prices if p.currency),
		key=lambda c: sum(1 for p in prices if p.currency == c),
		default="USD",
	)

	min_price = int(min_price / 10) * 10
	max_price = int((max_price + 9) / 10) * 10  # Round up

	return {"min_price": min_price, "max_price": max_price, "currency": currency}


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
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
