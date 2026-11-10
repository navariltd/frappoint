"""Property scoping.

Hotel data belongs to a Hotel Property. A user's properties come from Frappe User Permissions
on Hotel Property, with the usual Frappe meaning:

- no User Permission on Hotel Property: the user is not restricted (sees every property);
- one or more: the user sees only those properties.

System Manager and Administrator are never restricted.

Frappe already filters list views and link fields by User Permission. These helpers cover what it
does not: raw SQL in services, whitelisted APIs, and the `permission_query_conditions` /
`has_permission` hooks that hooks.py wires for every DocType in PROPERTY_SCOPED_DOCTYPES.
"""

import frappe
from frappe import _

from frappoint.vuna_hospitality.constants import PROPERTY_DOCTYPE, PROPERTY_FIELD, UNRESTRICTED_ROLES


def get_user_properties(user: str | None = None) -> list[str] | None:
	"""Return the properties `user` may access, or None when the user is not restricted."""
	user = user or frappe.session.user
	if user == "Administrator" or set(UNRESTRICTED_ROLES) & set(frappe.get_roles(user)):
		return None

	if not frappe.db.exists("DocType", PROPERTY_DOCTYPE):
		return None

	permissions = frappe.permissions.get_user_permissions(user).get(PROPERTY_DOCTYPE) or []
	properties = sorted({row.get("doc") for row in permissions if row.get("doc")})
	return properties or None


def can_access_property(property_name: str | None, user: str | None = None) -> bool:
	allowed = get_user_properties(user)
	return allowed is None or (bool(property_name) and property_name in allowed)


def assert_property_access(property_name: str | None, user: str | None = None) -> None:
	"""Raise PermissionError unless `user` may work with `property_name`. Call at the top of APIs."""
	if not can_access_property(property_name, user):
		raise frappe.PermissionError(_("You do not have access to property {0}.").format(property_name))


def scope_filters(filters: dict | None = None, user: str | None = None) -> dict:
	"""Add the user's property restriction to a `frappe.get_all`-style filters dict."""
	filters = dict(filters or {})
	allowed = get_user_properties(user)
	if allowed is None:
		return filters

	requested = filters.get(PROPERTY_FIELD)
	if isinstance(requested, str):
		filters[PROPERTY_FIELD] = requested if requested in allowed else ["in", []]
	else:
		filters[PROPERTY_FIELD] = ["in", allowed]
	return filters


def get_permission_query_conditions(user: str | None = None, doctype: str | None = None) -> str:
	"""`permission_query_conditions` hook for property-scoped DocTypes."""
	allowed = get_user_properties(user)
	if allowed is None or not doctype:
		return ""
	if not allowed:
		return "1=0"

	values = ", ".join(frappe.db.escape(name) for name in allowed)
	return f"`tab{doctype}`.`{PROPERTY_FIELD}` in ({values})"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	"""`has_permission` hook for property-scoped DocTypes. Must return True to allow."""
	property_name = doc.get(PROPERTY_FIELD)
	if not property_name and doc.get("__islocal"):
		# A new document without a property yet; the required-field check rejects it on save.
		return True
	return can_access_property(property_name, user)
