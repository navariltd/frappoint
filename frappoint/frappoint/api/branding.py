import re

import frappe

COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
COLOR_FIELDS = (
	"primary_color",
	"primary_hover_color",
	"accent_color",
	"light_surface_color",
	"page_background_color",
	"body_text_color",
)


def _valid_color(value: str | None) -> str | None:
	if value and COLOR_PATTERN.fullmatch(value.strip()):
		return value.strip().lower()
	return None


def _get_branding(settings_doctype: str) -> dict:
	"""Return presentation-only branding from a settings DocType that uses the shared branding fields."""
	settings = frappe.get_cached_doc(settings_doctype)
	branding = {
		"company": settings.get("company"),
		"page_title": settings.get("page_title"),
		"sidebar_logo": settings.get("sidebar_logo"),
		"favicon": settings.get("favicon"),
		"use_24_hour_clock_system": bool(settings.get("use_24_hour_clock_system")),
	}

	for field in COLOR_FIELDS:
		branding[field] = _valid_color(settings.get(field))

	return branding


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_booking_desk_branding() -> dict:
	"""Return the public, presentation-only Booking Desk branding settings."""
	return _get_branding("Booking Desk Settings")


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_hospitality_branding() -> dict:
	"""Return the public, presentation-only Hospitality app branding settings."""
	branding = _get_branding("Hospitality Settings")
	branding["enabled"] = bool(frappe.get_cached_doc("Hospitality Settings").get("enable_hospitality"))
	return branding
