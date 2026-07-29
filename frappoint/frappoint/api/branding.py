import re

import frappe

COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


def _valid_color(value: str | None) -> str | None:
	if value and COLOR_PATTERN.fullmatch(value.strip()):
		return value.strip().lower()
	return None


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_booking_desk_branding() -> dict:
	"""Return the public, presentation-only Booking Desk branding settings."""
	settings = frappe.get_cached_doc("Booking Desk Settings")
	branding = {
		"company": settings.get("company"),
		"page_title": settings.get("page_title"),
		"sidebar_logo": settings.get("sidebar_logo"),
		"favicon": settings.get("favicon"),
	}

	for field in (
		"primary_color",
		"primary_hover_color",
		"accent_color",
		"light_surface_color",
		"page_background_color",
		"body_text_color",
	):
		branding[field] = _valid_color(settings.get(field))

	return branding
