# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

HOSPITALITY_DESKTOP_ICON = "Hospitality"
HOSPITALITY_WORKSPACE = "Hospitality"
HOSPITALITY_SIDEBAR = "Hospitality"
FRAPPOINT_DOCK = "frappoint"
TAPE_CHART_DAYS_RANGE = (7, 62)
MIN_BOARD_REFRESH_SECONDS = 15


class HospitalitySettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accent_color: DF.Color
		allow_room_charge_for_services: DF.Check
		allow_walk_ins: DF.Check
		board_refresh_seconds: DF.Int
		body_text_color: DF.Color
		company: DF.Link | None
		default_landing_page: DF.Literal["Front Desk Today", "Tape Chart", "Reservations"]
		enable_hospitality: DF.Check
		enable_preference_room_ranking: DF.Check
		enable_preference_suggestions: DF.Check
		favicon: DF.AttachImage | None
		hold_expiry_minutes: DF.Int
		id_document_retention_days: DF.Int
		light_surface_color: DF.Color
		max_advance_booking_days: DF.Int
		max_stay_nights: DF.Int
		page_background_color: DF.Color
		page_title: DF.Data
		primary_color: DF.Color
		primary_hover_color: DF.Color
		sidebar_logo: DF.AttachImage | None
		suggestion_min_occurrences: DF.Int
		tape_chart_days: DF.Int
		use_24_hour_clock_system: DF.Check
	# end: auto-generated types

	def validate(self):
		self.validate_front_desk()
		self.validate_reservations()
		self.validate_suggestions()

	def validate_front_desk(self):
		low, high = TAPE_CHART_DAYS_RANGE
		if not low <= (self.tape_chart_days or 0) <= high:
			frappe.throw(_("Tape Chart Days must be between {0} and {1}.").format(low, high))

		if self.board_refresh_seconds and self.board_refresh_seconds < MIN_BOARD_REFRESH_SECONDS:
			frappe.throw(
				_("Board Refresh Interval must be 0 (off) or at least {0} seconds.").format(
					MIN_BOARD_REFRESH_SECONDS
				)
			)

	def validate_reservations(self):
		for fieldname in ("hold_expiry_minutes", "max_advance_booking_days", "max_stay_nights"):
			if (self.get(fieldname) or 0) < 1:
				frappe.throw(_("{0} must be at least 1.").format(_(self.meta.get_label(fieldname))))

	def validate_suggestions(self):
		if self.enable_preference_suggestions and (self.suggestion_min_occurrences or 0) < 1:
			frappe.throw(_("Minimum Occurrences for a Suggestion must be at least 1."))

	def on_update(self):
		# Turning the module on or off changes which workspaces, routes, and fields are visible,
		# so desk caches must be rebuilt for every user.
		if self.has_value_changed("enable_hospitality"):
			sync_hospitality_visibility(self.enable_hospitality)
			self.log_module_toggle()
			frappe.clear_cache()

	def log_module_toggle(self):
		from frappoint.vuna_hospitality.services.event_log import log_event

		if not frappe.db.exists("DocType", "Hospitality Event Log"):
			return  # first migrate, before the log DocType is synced
		log_event(
			self.doctype,
			self.name,
			"Module Enabled" if self.enable_hospitality else "Module Disabled",
			data={"enable_hospitality": self.enable_hospitality},
		)


def is_hospitality_enabled() -> bool:
	"""Return True when the hospitality module is switched on for this site.

	Hotel jobs, routes, and hooks should call this first and exit when it returns False.
	"""
	return bool(frappe.db.get_single_value("Hospitality Settings", "enable_hospitality", cache=True))


def sync_hospitality_visibility(enabled: bool | int | None = None) -> None:
	"""Show the Hospitality desktop icon, workspace and dock entry only while the module is enabled.

	Uses `db.set_value` so the shipped JSON files (which start hidden) are not re-exported
	in developer mode. Also runs after every migrate, because a fresh install or a re-imported
	icon file must follow the site's current setting.
	"""
	if enabled is None:
		enabled = frappe.db.get_single_value("Hospitality Settings", "enable_hospitality")
	hidden = 0 if enabled else 1

	if frappe.db.exists("Desktop Icon", HOSPITALITY_DESKTOP_ICON):
		frappe.db.set_value("Desktop Icon", HOSPITALITY_DESKTOP_ICON, "hidden", hidden)
		from frappe.desk.doctype.desktop_icon.desktop_icon import clear_every_users_desktop_icons

		clear_every_users_desktop_icons()

	if frappe.db.exists("Workspace", HOSPITALITY_WORKSPACE):
		frappe.db.set_value("Workspace", HOSPITALITY_WORKSPACE, "is_hidden", hidden)

	# "Apps" desktop mode: Hospitality is an entry on the Frappoint app's dock (rail).
	dock_item = frappe.db.get_value(
		"Dock Item",
		{
			"parenttype": "Dock",
			"parent": FRAPPOINT_DOCK,
			"link_type": "Sidebar",
			"link_to": HOSPITALITY_SIDEBAR,
		},
		"name",
	)
	if dock_item:
		frappe.db.set_value("Dock Item", dock_item, "hidden", hidden)
		frappe.clear_document_cache("Dock", FRAPPOINT_DOCK)
		from frappe.desk.doctype.dock.dock import drop_dock_caches

		drop_dock_caches(None)
