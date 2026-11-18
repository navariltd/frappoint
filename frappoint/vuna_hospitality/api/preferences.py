"""Guest preferences, stay requests, suggestions and guest history matching (feature F18).

The stay page shows a guest's declared preferences first, then observed suggestions with their
evidence. Each command returns the refreshed panel. Who may do what is checked in the services:
reservations and front-desk roles edit, and sensitive preferences need the roles that see a
guest's sensitive details.
"""

import frappe
from frappe import _
from frappe.utils import sbool

from frappoint.vuna_hospitality.services import guest_history, preferences, suggestions
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.inventory import run_with_inventory_retry
from frappoint.vuna_hospitality.services.property_scope import assert_property_access

STAY = "Stay Reservation"
PROFILE = "Guest Profile"


def _stay(stay: str) -> frappe._dict:
	row = frappe.db.get_value(STAY, stay, ["name", "property", "lead_guest"], as_dict=True)
	if not row:
		raise frappe.DoesNotExistError(_("Stay Reservation {0} does not exist.").format(stay))
	assert_property_access(row.property)
	if not frappe.has_permission(STAY, "read", doc=stay):
		raise frappe.PermissionError(_("You are not allowed to see stay {0}.").format(stay))
	return row


def _check_profile(guest_profile: str, stay: frappe._dict | None = None) -> None:
	if not frappe.db.exists(PROFILE, guest_profile):
		raise frappe.DoesNotExistError(_("Guest Profile {0} does not exist.").format(guest_profile))
	if stay and (
		guest_profile == stay.lead_guest
		or frappe.db.exists("Stay Guest", {"stay_reservation": stay.name, "guest_profile": guest_profile})
	):
		return
	if not frappe.has_permission(PROFILE, "read", doc=guest_profile):
		raise frappe.PermissionError(_("You are not allowed to see guest {0}.").format(guest_profile))


def _insights(guest_profile: str | None, stay: str | None) -> dict:
	row = _stay(stay) if stay else None
	guest_profile = guest_profile or (row.lead_guest if row else None)
	if not guest_profile:
		return {"guest_profile": None, "declared": [], "requests": [], "suggestions": []}
	_check_profile(guest_profile, row)
	return suggestions.guest_insights(guest_profile, row.name if row else None)


def _command(fn, guest_profile: str | None, stay: str | None) -> dict:
	run_with_inventory_retry(fn)
	return _insights(guest_profile, stay)


@frappe.whitelist()
@require_hospitality
def get_guest_insights(guest_profile: str | None = None, stay: str | None = None) -> dict:
	"""Declared preferences, this stay's requests, and observed suggestions with evidence."""
	return _insights(guest_profile, stay)


@frappe.whitelist()
@require_hospitality
def get_preference_options() -> dict:
	"""What the preference form offers: categories, priorities and room features."""
	return {
		"categories": [
			*preferences.ROOM_CATEGORIES,
			"Dietary",
			"Service Type",
			"Provider",
			"Language",
			"Other",
		],
		"room_categories": list(preferences.ROOM_CATEGORIES),
		"priorities": list(reversed(preferences.PRIORITIES)),
		"room_features": preferences.room_feature_options(),
		"can_edit": preferences.can_edit(),
		"can_see_sensitive": preferences.can_see_sensitive(),
	}


# --------------------------------------------------------------------------- preferences


@frappe.whitelist(methods=["POST"])
@require_hospitality
def add_guest_preference(
	guest_profile: str,
	category: str,
	value: str | None = None,
	priority: str = "Normal",
	room_feature: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	sensitive: bool = False,
	this_property_only: bool = False,
	stay: str | None = None,
	notes: str | None = None,
) -> dict:
	row = _stay(stay) if stay else None
	_check_profile(guest_profile, row)
	return _command(
		lambda: preferences.add_preference(
			guest_profile,
			category,
			value,
			priority=priority,
			room_feature=room_feature or None,
			reference_doctype=reference_doctype or None,
			reference_name=reference_name or None,
			sensitivity=preferences.SENSITIVE if sbool(sensitive) else "Normal",
			property_name=row.property if row and sbool(this_property_only) else None,
			source="Staff confirmed" if stay else "Guest stated",
			notes=notes,
		),
		guest_profile,
		stay,
	)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def retire_guest_preference(preference: str, reason: str | None = None, stay: str | None = None) -> dict:
	guest_profile = frappe.db.get_value(preferences.PREFERENCE, preference, "guest_profile")
	if not guest_profile:
		raise frappe.DoesNotExistError(_("Guest Preference {0} does not exist.").format(preference))
	_check_profile(guest_profile, _stay(stay) if stay else None)
	return _command(lambda: preferences.retire_preference(preference, reason), guest_profile, stay)


# --------------------------------------------------------------------------- stay requests


@frappe.whitelist(methods=["POST"])
@require_hospitality
def add_stay_request(
	stay: str,
	category: str,
	value: str | None = None,
	priority: str = "Normal",
	room_feature: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	notes: str | None = None,
) -> dict:
	_stay(stay)
	return _command(
		lambda: preferences.add_stay_request(
			stay,
			category,
			value,
			priority=priority,
			room_feature=room_feature or None,
			reference_doctype=reference_doctype or None,
			reference_name=reference_name or None,
			notes=notes,
		),
		None,
		stay,
	)


def _request_stay(request: str) -> str:
	stay = frappe.db.get_value(preferences.REQUEST, request, "stay_reservation")
	if not stay:
		raise frappe.DoesNotExistError(_("Stay Request {0} does not exist.").format(request))
	_stay(stay)
	return stay


@frappe.whitelist(methods=["POST"])
@require_hospitality
def close_stay_request(request: str, status: str = "Done", notes: str | None = None) -> dict:
	stay = _request_stay(request)
	return _command(lambda: preferences.close_stay_request(request, status, notes), None, stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def copy_request_to_profile(request: str, sensitive: bool = False) -> dict:
	"""Keep a this-stay request on the guest's profile for every stay."""
	stay = _request_stay(request)
	sensitivity = preferences.SENSITIVE if sbool(sensitive) else "Normal"
	return _command(lambda: preferences.copy_request_to_profile(request, sensitivity), None, stay)


# --------------------------------------------------------------------------- suggestions


@frappe.whitelist(methods=["POST"])
@require_hospitality
def apply_suggestion(stay: str, key: str, evidence: str | None = None) -> dict:
	"""Use a suggestion for this stay only. It becomes an open request; nothing is booked or charged."""
	_stay(stay)
	return _command(lambda: suggestions.apply_to_stay(stay, key, evidence), None, stay)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def save_suggestion(
	guest_profile: str, key: str, evidence: str | None = None, stay: str | None = None
) -> dict:
	row = _stay(stay) if stay else None
	_check_profile(guest_profile, row)
	return _command(
		lambda: suggestions.save_to_profile(guest_profile, key, evidence, stay), guest_profile, stay
	)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def dismiss_suggestion(
	guest_profile: str, key: str, evidence: str | None = None, stay: str | None = None
) -> dict:
	row = _stay(stay) if stay else None
	_check_profile(guest_profile, row)
	return _command(lambda: suggestions.dismiss(guest_profile, key, evidence, stay), guest_profile, stay)


# --------------------------------------------------------------------------- guest history matching


def _check_review() -> None:
	if not guest_history.can_review():
		raise frappe.PermissionError(_("You are not allowed to review guest history matches."))


@frappe.whitelist()
@require_hospitality
def get_history_matches(limit: int = 100) -> dict:
	"""Appointment guests proposed as Guest Profiles, waiting for someone to confirm them."""
	_check_review()
	return {"matches": guest_history.proposed_matches(limit)}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def find_history_matches() -> dict:
	"""Look for more appointment guests whose email or phone identifies one profile."""
	_check_review()
	created = guest_history.propose_matches()
	return {"created": created or 0, "matches": guest_history.proposed_matches()}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def review_history_match(match: str, confirm: bool) -> dict:
	_check_review()
	guest_history.review_match(match, sbool(confirm))
	return {"matches": guest_history.proposed_matches()}
