import frappe


def sync_service_type_item_group(doc, method=None):
	"""Keep the fetched Service Type group in sync when its linked Item changes."""
	if not doc.has_value_changed("item_group"):
		return

	# Update derived data without running unrelated Service Type validations.
	# set_value also updates modified and clears the document cache.
	frappe.db.set_value("Service Type", {"item": doc.name}, "item_group", doc.item_group)
