# Copyright (c) 2026, Navari LTD and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from frappoint.frappoint.api.branding import get_booking_desk_branding, get_hospitality_branding
from frappoint.vuna_hospitality.doctype.hospitality_settings.hospitality_settings import (
	HOSPITALITY_DESKTOP_ICON,
	HOSPITALITY_WORKSPACE,
	sync_hospitality_visibility,
)

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company"]


def _settings(**overrides):
	values = {
		"doctype": "Hospitality Settings",
		"page_title": "Front Desk",
		"tape_chart_days": 14,
		"board_refresh_seconds": 60,
		"hold_expiry_minutes": 15,
		"max_advance_booking_days": 365,
		"max_stay_nights": 30,
		"enable_preference_suggestions": 1,
		"suggestion_min_occurrences": 2,
	}
	values.update(overrides)
	return frappe.get_doc(values)


class IntegrationTestHospitalitySettings(IntegrationTestCase):
	def test_defaults_are_valid(self):
		_settings().validate()

	def test_tape_chart_days_out_of_range(self):
		for days in (6, 63):
			with self.subTest(days=days), self.assertRaises(frappe.ValidationError):
				_settings(tape_chart_days=days).validate()

	def test_board_refresh_can_be_off_but_not_too_fast(self):
		_settings(board_refresh_seconds=0).validate()
		with self.assertRaises(frappe.ValidationError):
			_settings(board_refresh_seconds=5).validate()

	def test_reservation_limits_must_be_positive(self):
		for fieldname in ("hold_expiry_minutes", "max_advance_booking_days", "max_stay_nights"):
			with self.subTest(fieldname=fieldname), self.assertRaises(frappe.ValidationError):
				_settings(**{fieldname: 0}).validate()

	def test_suggestion_threshold_required_only_when_enabled(self):
		with self.assertRaises(frappe.ValidationError):
			_settings(suggestion_min_occurrences=0).validate()
		_settings(enable_preference_suggestions=0, suggestion_min_occurrences=0).validate()


class TestHospitalityVisibility(IntegrationTestCase):
	def _sync(self, enabled):
		with (
			patch("frappe.db.exists", return_value=True),
			patch("frappe.db.get_value", return_value="dock-item-1"),
			patch("frappe.db.set_value") as set_value,
			patch("frappe.clear_document_cache"),
			patch("frappe.desk.doctype.dock.dock.drop_dock_caches"),
			patch(
				"frappe.desk.doctype.desktop_icon.desktop_icon.clear_every_users_desktop_icons"
			) as clear_icons,
		):
			sync_hospitality_visibility(enabled)
		return set_value, clear_icons

	def test_disabled_hides_icon_and_workspace(self):
		set_value, clear_icons = self._sync(0)
		set_value.assert_any_call("Desktop Icon", HOSPITALITY_DESKTOP_ICON, "hidden", 1)
		set_value.assert_any_call("Workspace", HOSPITALITY_WORKSPACE, "is_hidden", 1)
		set_value.assert_any_call("Dock Item", "dock-item-1", "hidden", 1)
		clear_icons.assert_called_once()

	def test_enabled_shows_icon_and_workspace(self):
		set_value, _clear_icons = self._sync(1)
		set_value.assert_any_call("Desktop Icon", HOSPITALITY_DESKTOP_ICON, "hidden", 0)
		set_value.assert_any_call("Workspace", HOSPITALITY_WORKSPACE, "is_hidden", 0)
		set_value.assert_any_call("Dock Item", "dock-item-1", "hidden", 0)


class TestBranding(IntegrationTestCase):
	def _branding_doc(self, **overrides):
		values = {
			"company": "Test Co",
			"page_title": "Desk",
			"sidebar_logo": "/files/logo.png",
			"favicon": "/files/favicon.png",
			"use_24_hour_clock_system": 1,
			"primary_color": "#8A0E04",
			"primary_hover_color": "not-a-color",
			"accent_color": "#a06f22",
			"light_surface_color": "#feffff",
			"page_background_color": "#f8f4ee",
			"body_text_color": "#2d2d2d",
			"enable_hospitality": 1,
		}
		values.update(overrides)
		return frappe._dict(values)

	def test_booking_desk_and_hospitality_share_the_same_shape(self):
		with patch("frappe.get_cached_doc", return_value=self._branding_doc()):
			desk = get_booking_desk_branding()
			hospitality = get_hospitality_branding()

		self.assertEqual(set(hospitality) - set(desk), {"enabled"})
		self.assertEqual(hospitality["primary_color"], "#8a0e04")
		self.assertIsNone(hospitality["primary_hover_color"])
		self.assertTrue(hospitality["use_24_hour_clock_system"])
		self.assertTrue(hospitality["enabled"])

	def test_hospitality_branding_reports_disabled(self):
		with patch("frappe.get_cached_doc", return_value=self._branding_doc(enable_hospitality=0)):
			self.assertFalse(get_hospitality_branding()["enabled"])
