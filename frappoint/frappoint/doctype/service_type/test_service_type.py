# Copyright (c) 2025, Navari LTD and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from frappoint.frappoint.api.service_type import (
	_safe_portal_html,
	_service_image_url,
	get_service_type_details,
	get_service_type_image,
)


class TestServiceType(FrappeTestCase):
	def test_service_image_urls_support_public_and_private_files(self):
		self.assertEqual(
			_service_image_url("Massage Therapy", "/private/files/service.jpg"),
			"/api/method/frappoint.frappoint.api.service_type.get_service_type_image"
			"?service_type=Massage%20Therapy",
		)
		self.assertEqual(
			_service_image_url("Massage Therapy", "/files/service.jpg"),
			"/files/service.jpg",
		)

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
		self.assertEqual(
			result["image"],
			"/api/method/frappoint.frappoint.api.service_type.get_service_type_image" "?service_type=Massage",
		)
		self.assertEqual(result["tags"], ["Relaxation", "Wellness"])
		get_providers.assert_called_once_with("Massage")

	@patch("frappoint.frappoint.api.service_type.frappe.get_doc")
	@patch("frappoint.frappoint.api.service_type.frappe.db.get_value")
	def test_private_service_image_is_streamed_inline(self, get_value, get_doc):
		get_value.side_effect = ["/private/files/massage.jpg", "FILE-0001"]
		get_doc.return_value.get_content.return_value = b"image-content"

		get_service_type_image("Massage")

		self.assertEqual(frappe.local.response.filename, "massage.jpg")
		self.assertEqual(frappe.local.response.filecontent, b"image-content")
		self.assertEqual(frappe.local.response.content_type, "image/jpeg")
		self.assertEqual(frappe.local.response.display_content_as, "inline")
		self.assertEqual(frappe.local.response.type, "download")
