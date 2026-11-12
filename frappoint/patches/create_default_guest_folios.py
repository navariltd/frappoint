"""Give stays confirmed before folios existed (F7) their default folio, so check-out can check it."""

import frappe

ACTIVE_STATUSES = ("Confirmed", "Due In", "In House", "Due Out")


def execute():
	if not frappe.db.exists("DocType", "Guest Folio"):
		return

	from frappoint.vuna_hospitality.services.folio import ensure_default_folio

	stays = frappe.get_all(
		"Stay Reservation",
		filters={"status": ["in", ACTIVE_STATUSES], "default_folio": ["is", "not set"]},
		pluck="name",
	)
	for stay in stays:
		ensure_default_folio(stay)
