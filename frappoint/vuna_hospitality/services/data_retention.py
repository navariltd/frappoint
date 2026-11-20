"""Keep identity documents no longer than needed (design §23.4; plan F20).

A guest's ID document (type, number and its masked hint) is removed from their profile once
`id_document_retention_days` (Hospitality Settings) have passed since their last stay ended, or
since the profile was created when they never stayed. A guest with a stay that is booked or in
progress keeps theirs. Zero days means keep them.

The statutory Guest Register Entry is not touched: the law keeps it for its own period.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, today
from frappe.utils.password import remove_encrypted_password

from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.feature_flag import hospitality_job

PROFILE = "Guest Profile"
STAY = "Stay Reservation"
ACTIVE_STAY_STATUSES = ("Held", "Confirmed", "Due In", "In House", "Due Out")
BATCH = 500


def retention_days() -> int:
	return cint(frappe.db.get_single_value("Hospitality Settings", "id_document_retention_days"))


def due_profiles(on_date=None, limit: int = BATCH) -> list[str]:
	"""Profiles holding an ID document whose retention period has ended."""
	days = retention_days()
	if days <= 0:
		return []
	cutoff = add_days(getdate(on_date or today()), -days)
	candidates = frappe.get_all(
		PROFILE,
		or_filters={"id_document_type": ["is", "set"], "id_document_hint": ["is", "set"]},
		fields=["name", "creation"],
		order_by="creation asc",
		limit_page_length=limit * 4,
	)
	due, seen = [], set()
	for row in candidates:
		if row.name in seen:
			continue
		seen.add(row.name)
		stays = frappe.get_all("Stay Guest", filters={"guest_profile": row.name}, pluck="stay_reservation")
		stay_rows = (
			frappe.get_all(STAY, filters={"name": ["in", stays or [""]]}, fields=["status", "departure_date"])
			if stays
			else []
		)
		if any(stay.status in ACTIVE_STAY_STATUSES for stay in stay_rows):
			continue
		last = max((getdate(stay.departure_date) for stay in stay_rows), default=getdate(row.creation))
		if last <= cutoff:
			due.append(row.name)
		if len(due) >= limit:
			break
	return due


def purge(profile: str) -> None:
	"""Remove the profile's ID document and record that it was removed (not what it was)."""
	frappe.db.set_value(
		PROFILE,
		profile,
		{"id_document_type": None, "id_document_hint": None, "id_document_number": None},
		update_modified=False,
	)
	remove_encrypted_password(PROFILE, profile, "id_document_number")
	log_event(
		PROFILE,
		profile,
		"ID Document Removed",
		reason=_("Retention period of {0} days ended").format(retention_days()),
		data={"fields": ["id_document_type", "id_document_number", "id_document_hint"]},
	)


@hospitality_job
def purge_expired_id_documents() -> int:
	"""Daily: remove ID documents past their retention period."""
	names = due_profiles()
	for name in names:
		purge(name)
	return len(names)
