import frappe
from frappe import _


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
			"description",
			"default_duration_in_minutes",
			"item_name",
			"item_group",
			"disabled",
		],
		order_by="appointment_type",
	)

	for service in service_types:
		prices = frappe.get_all(
			"Service Type Price",
			filters={"parent": service.name},
			fields=["rate", "currency", "price_list"],
			limit=1,
		)
		service["price"] = prices[0] if prices else None

		unit_types = frappe.get_all(
			"Service Type Unit Type",
			filters={"parent": service.name},
			fields=["service_unit_type", "capacity"],
		)
		service["requires_service_unit"] = len(unit_types) > 0
		service["service_unit_types"] = unit_types

	return service_types


@frappe.whitelist(allow_guest=True)
def get_service_type_details(service_type):
	"""
	Get detailed information about a specific service type
	Use case: Service detail page, booking form
	"""
	doc = frappe.get_doc("Service Type", service_type)

	return {
		"name": doc.name,
		"appointment_type": doc.appointment_type,
		"description": doc.description,
		"default_duration_in_minutes": doc.default_duration_in_minutes,
		"max_clients_per_slot": doc.max_clients_per_slot,
		"buffer_before": doc.buffer_before,
		"buffer_after": doc.buffer_after,
		"disabled": doc.disabled,
		"prices": [
			{"rate": p.rate, "currency": p.currency, "price_list": p.price_list, "uom": p.uom}
			for p in doc.prices
		],
		"service_unit_types": [
			{
				"service_unit_type": u.service_unit_type,
				"capacity": u.capacity,
			}
			for u in doc.service_unit_types
		],
		"materials": [
			{"item": m.item, "item_name": m.item_name, "qty": m.qty, "uom": m.uom} for m in doc.consumables
		],
	}
