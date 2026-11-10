"""Session context for the hospitality front-end app."""

import frappe

from frappoint.vuna_hospitality.constants import HOSPITALITY_ROLES
from frappoint.vuna_hospitality.services.feature_flag import is_hospitality_enabled
from frappoint.vuna_hospitality.services.property_scope import get_user_properties


@frappe.whitelist()
def get_session_context() -> dict:
	"""What the hospitality app needs on load: is the module on, and what may this user do.

	Returns `enabled: False` instead of raising, so the app can show a "not enabled" screen.
	`properties` is None when the user is not restricted to specific properties.
	"""
	user = frappe.session.user
	user_roles = set(frappe.get_roles(user))
	return {
		"enabled": is_hospitality_enabled(),
		"user": user,
		"roles": sorted(user_roles & {*HOSPITALITY_ROLES, "System Manager"}),
		"properties": get_user_properties(user),
	}
