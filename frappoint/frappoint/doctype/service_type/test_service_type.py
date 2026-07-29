# Copyright (c) 2025, Navari LTD and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from frappoint.frappoint.api.service_type import (
	_public_asset_url,
	_safe_portal_html,
	get_service_type_details,
)


class TestServiceType(FrappeTestCase):
	def test_private_assets_are_not_exposed_to_portal(self):
		self.assertIsNone(_public_asset_url("/private/files/service.jpg"))
		self.assertEqual(_public_asset_url("/files/service.jpg"), "/files/service.jpg")

	def test_portal_html_is_sanitized(self):
		sanitized = _safe_portal_html('<p onclick="alert(1)">Safe</p><script>alert("unsafe")</script>')

		self.assertIn("<p>Safe</p>", sanitized)
		self.assertNotIn("onclick", sanitized)
		self.assertNotIn("<script", sanitized)

	@patch("frappoint.frappoint.api.service_type.get_payment_gateways_for_service_type")
	@patch("frappoint.frappoint.api.service_type.get_providers_for_service")
	@patch("frappoint.frappoint.api.service_type.frappe.db.get_all")
	@patch("frappoint.frappoint.api.service_type.frappe.db.get_value")
	def test_service_details_are_active_and_portal_safe(
		self,
		get_value,
		get_all,
		get_providers,
		get_payment_gateways,
	):
		get_value.return_value = frappe._dict(
			name="Massage",
			appointment_type="Massage",
			item_name="Massage",
			item_group="Treatments",
			company="Configured Company",
			short_description="Restorative treatment",
			image="/private/files/massage.jpg",
			tags="Relaxation, Wellness",
			description="<p>Description</p>",
			default_duration_in_minutes=60,
			min_guests=1,
			max_guests=2,
			confirmation_deposit_percent=20,
			benefits="<ul><li>Relaxation</li></ul>",
			techniques="<ul><li>Massage</li></ul>",
		)
		get_all.return_value = [
			frappe._dict(
				price_name="60 minutes",
				amount=100,
				duration=60,
				currency="KES",
				guest_count=1,
				pricing_model="Per Guest",
			)
		]
		get_providers.return_value = []
		get_payment_gateways.return_value = []

		result = get_service_type_details("Massage")

		self.assertEqual(
			get_value.call_args.args[1],
			{
				"name": "Massage",
				"disabled": 0,
			},
		)
		self.assertIsNone(result["image"])
		self.assertEqual(result["tags"], ["Relaxation", "Wellness"])
		get_providers.assert_called_once_with("Massage")
