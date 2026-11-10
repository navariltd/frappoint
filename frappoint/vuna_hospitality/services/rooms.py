"""Room state rules for properties and rooms (design §9.1-9.2).

A room has three independent states, each stored as a read-only cache on Hotel Room:

- sellability: from submitted Room State Periods (Out of Order beats Out of Service);
- housekeeping_condition: set by housekeeping actions (F17 automates this);
- occupancy_status: set by stay actions (F5/F6).

They are only changed through the functions here, never by editing the room.
"""

import re

import frappe
from frappe import _
from frappe.utils import getdate

from frappoint.vuna_hospitality.constants import (
	FRONT_DESK_MANAGER,
	HOSPITALITY_MANAGER,
	HOUSEKEEPING_ATTENDANT,
	HOUSEKEEPING_SUPERVISOR,
)
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.feature_flag import hospitality_job, require_hospitality
from frappoint.vuna_hospitality.services.property_scope import assert_property_access

CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,9}$")

SELLABLE = "Sellable"
OUT_OF_SERVICE = "Out of Service"
OUT_OF_ORDER = "Out of Order"

HOUSEKEEPING_CONDITIONS = ("Inspected", "Clean", "Pickup", "Dirty")
HOUSEKEEPING_ROLES = {
	"System Manager",
	HOSPITALITY_MANAGER,
	FRONT_DESK_MANAGER,
	HOUSEKEEPING_SUPERVISOR,
	HOUSEKEEPING_ATTENDANT,
}

# Read-only on Hotel Room; changed only with db_set by the functions in this module.
STATE_FIELDS = ("sellability", "housekeeping_condition", "occupancy_status")


def normalize_code(value: str | None, label: str) -> str:
	"""Upper-case a property or room-type code and check its shape."""
	code = (value or "").strip().upper()
	if not CODE_PATTERN.match(code):
		frappe.throw(
			_(
				"{0} must be 2 to 10 characters: letters, digits and hyphens, starting with a letter or digit."
			).format(_(label))
		)
	return code


def get_business_date(property_name: str):
	return getdate(frappe.db.get_value("Hotel Property", property_name, "business_date"))


def get_sellability(room: str, on_date=None) -> str:
	"""Sellability of `room` on `on_date` (default: its property's business date)."""
	if on_date is None:
		on_date = get_business_date(frappe.db.get_value("Hotel Room", room, "property"))
	states = set(
		frappe.get_all(
			"Room State Period",
			filters={
				"room": room,
				"docstatus": 1,
				"from_date": ["<=", on_date],
				"to_date": [">", on_date],
			},
			pluck="state",
		)
	)
	if OUT_OF_ORDER in states:
		return OUT_OF_ORDER
	if OUT_OF_SERVICE in states:
		return OUT_OF_SERVICE
	return SELLABLE


def refresh_room_sellability(room: str, on_date=None) -> str:
	"""Recompute and store a room's sellability. Returns the new value."""
	sellability = get_sellability(room, on_date)
	if frappe.db.get_value("Hotel Room", room, "sellability") != sellability:
		frappe.db.set_value("Hotel Room", room, "sellability", sellability)
	return sellability


@hospitality_job
def refresh_all_sellability():
	"""Daily job: periods start and end as dates pass, so recompute every active room."""
	for prop in frappe.get_all("Hotel Property", filters={"is_active": 1}, fields=["name", "business_date"]):
		for room in frappe.get_all("Hotel Room", filters={"property": prop.name}, pluck="name"):
			refresh_room_sellability(room, getdate(prop.business_date))


@frappe.whitelist()
@require_hospitality
def set_housekeeping_condition(room: str, condition: str, reason: str | None = None) -> dict:
	"""Record a room's housekeeping condition (Inspected, Clean, Pickup, Dirty)."""
	if condition not in HOUSEKEEPING_CONDITIONS:
		frappe.throw(
			_("Housekeeping condition must be one of: {0}.").format(", ".join(HOUSEKEEPING_CONDITIONS))
		)
	if not HOUSEKEEPING_ROLES & set(frappe.get_roles()):
		raise frappe.PermissionError(_("You are not allowed to change a room's housekeeping condition."))

	doc = frappe.get_doc("Hotel Room", room)
	assert_property_access(doc.property)
	previous = doc.housekeeping_condition
	if previous == condition:
		return {"room": room, "housekeeping_condition": condition, "changed": False}

	doc.db_set("housekeeping_condition", condition)
	log_event(
		"Hotel Room",
		room,
		"Housekeeping Condition Changed",
		from_status=previous,
		to_status=condition,
		reason=reason,
		property_name=doc.property,
	)
	return {"room": room, "housekeeping_condition": condition, "changed": True}


def update_room_type_counts(*room_types: str | None) -> None:
	"""Store the number of active rooms on each given Room Type."""
	for room_type in {rt for rt in room_types if rt}:
		count = frappe.db.count("Hotel Room", {"room_type": room_type, "is_active": 1})
		frappe.db.set_value("Room Type", room_type, "room_count", count, update_modified=False)
