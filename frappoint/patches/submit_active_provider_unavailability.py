from __future__ import annotations

import frappe


def execute():
	if not frappe.db.exists("DocType", "Service Provider Unavailability"):
		return

	names = frappe.get_all(
		"Service Provider Unavailability",
		filters={"status": "Active", "docstatus": 0},
		pluck="name",
	)
	for name in names:
		doc = frappe.get_doc("Service Provider Unavailability", name)
		doc.submit()

	if names:
		frappe.db.commit()
