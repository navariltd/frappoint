from unittest import TestCase
from unittest.mock import patch

import frappe

from frappoint.vuna_hospitality.services import property_scope

MODULE = "frappoint.vuna_hospitality.services.property_scope"


class TestPropertyScope(TestCase):
	def _scope(self, roles, user_properties, property_doctype_exists=True):
		"""Patch roles, User Permissions, and whether Hotel Property exists."""
		permissions = {"Hotel Property": [{"doc": name} for name in user_properties]}
		return (
			patch(f"{MODULE}.frappe.get_roles", return_value=roles),
			patch(f"{MODULE}.frappe.permissions.get_user_permissions", return_value=permissions),
			patch(f"{MODULE}.frappe.db.exists", return_value=property_doctype_exists),
		)

	def _run(self, fn, roles=("Front Desk Agent",), properties=("BEACH",), exists=True):
		patches = self._scope(list(roles), list(properties), exists)
		with patches[0], patches[1], patches[2]:
			return fn()

	def test_restricted_user_sees_only_permitted_properties(self):
		self.assertEqual(
			self._run(
				lambda: property_scope.get_user_properties("agent@example.com"), properties=("CITY", "BEACH")
			),
			["BEACH", "CITY"],
		)

	def test_user_without_user_permissions_is_unrestricted(self):
		self.assertIsNone(
			self._run(lambda: property_scope.get_user_properties("a@example.com"), properties=())
		)

	def test_system_manager_is_unrestricted(self):
		self.assertIsNone(
			self._run(lambda: property_scope.get_user_properties("a@example.com"), roles=("System Manager",))
		)

	def test_unrestricted_until_hotel_property_exists(self):
		self.assertIsNone(
			self._run(lambda: property_scope.get_user_properties("a@example.com"), exists=False)
		)

	def test_assert_property_access(self):
		self._run(lambda: property_scope.assert_property_access("BEACH", "a@example.com"))
		with self.assertRaises(frappe.PermissionError):
			self._run(lambda: property_scope.assert_property_access("CITY", "a@example.com"))

	def test_scope_filters(self):
		self.assertEqual(
			self._run(lambda: property_scope.scope_filters({"status": "Open"}, "a@example.com")),
			{"status": "Open", "property": ["in", ["BEACH"]]},
		)
		self.assertEqual(
			self._run(lambda: property_scope.scope_filters({"property": "CITY"}, "a@example.com")),
			{"property": ["in", []]},
		)
		self.assertEqual(
			self._run(lambda: property_scope.scope_filters({}, "a@example.com"), properties=()),
			{},
		)

	def test_permission_query_conditions(self):
		condition = self._run(
			lambda: property_scope.get_permission_query_conditions("a@example.com", doctype="Hotel Room")
		)
		self.assertEqual(condition, "`tabHotel Room`.`property` in ('BEACH')")
		self.assertEqual(
			self._run(
				lambda: property_scope.get_permission_query_conditions("a@example.com", doctype="Hotel Room"),
				properties=(),
			),
			"",
		)

	def test_has_permission_hook_returns_true_or_false(self):
		allowed = frappe._dict(property="BEACH")
		denied = frappe._dict(property="CITY")
		self.assertIs(self._run(lambda: property_scope.has_permission(allowed, user="a@example.com")), True)
		self.assertIs(self._run(lambda: property_scope.has_permission(denied, user="a@example.com")), False)
