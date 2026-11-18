"""Declared guest preferences and this-stay requests (design §19.3, §30.19; plan F18).

- **Guest Preference**: what a guest asks for on every stay. Saved only by a confirmed action
  (staff typing it in, or accepting a suggestion), with its source, priority and sensitivity.
- **Stay Request**: what a guest asks for on this stay only. It belongs to the stay and reaches
  the profile only when staff copy it there.

Both say what they mean in terms the hotel can match: a Hotel Room Feature ("Step-free access"),
a Hotel Room, a Hotel Amenity, a floor rule ("High floor", "Low floor", or a number), or a
connecting room. Room ranking (room_ranking.py) reads them; a room preference nobody can match
is refused when it is saved, so ranking never silently ignores it.

Sensitive preferences (medical, accessibility, religious) are shown, and used for ranking, only
for roles that see a guest's sensitive details.
"""

import re

import frappe
from frappe import _
from frappe.utils import now_datetime, today

from frappoint.vuna_hospitality.constants import (
	GUEST_SERVICES_AGENT,
	RESERVATION_ROLES,
	SENSITIVE_PREFERENCE_ROLES,
)
from frappoint.vuna_hospitality.services.event_log import log_event

PREFERENCE = "Guest Preference"
REQUEST = "Stay Request"
SERVICE_FLAG = "from_preferences_service"

ROOM_CATEGORIES = ("Room", "Floor", "View", "Bed", "Noise", "Accessibility", "Smoking")
REFERENCE_DOCTYPES = ("Hotel Room", "Hotel Amenity", "Service Type", "Service Provider")
PRIORITIES = ("Required", "High", "Normal")
SENSITIVE = "Sensitive"
OPEN = "Open"
CLOSED_STATUSES = ("Done", "Cancelled")

# Who adds and changes preferences and stay requests.
PREFERENCE_ROLES = (*RESERVATION_ROLES, GUEST_SERVICES_AGENT)

HIGH_FLOOR = "high"
LOW_FLOOR = "low"

MATCH_FIELDS = (
	"name",
	"category",
	"value",
	"priority",
	"room_feature",
	"reference_doctype",
	"reference_name",
)


def can_see_sensitive(user: str | None = None) -> bool:
	return bool(set(SENSITIVE_PREFERENCE_ROLES) & set(frappe.get_roles(user)))


def can_edit(user: str | None = None) -> bool:
	return bool(set(PREFERENCE_ROLES) & set(frappe.get_roles(user)))


def _require_edit() -> None:
	if not can_edit():
		raise frappe.PermissionError(_("You are not allowed to change guest preferences."))


# --------------------------------------------------------------------------- matching rules


def floor_rule(value: str | None) -> str | int | None:
	""" "High floor" → high, "Low floor" or "ground floor" → low, "Floor 4" → 4, else None."""
	text = (value or "").strip().lower()
	if not text:
		return None
	if "high" in text or "top" in text or "upper" in text:
		return HIGH_FLOOR
	if "low" in text or "ground" in text or "bottom" in text:
		return LOW_FLOOR
	number = re.search(r"-?\d+", text)
	return int(number.group()) if number else None


def wants_connecting_room(row) -> bool:
	return row.get("category") == "Room" and "connect" in (row.get("value") or "").lower()


def is_room_matchable(row) -> bool:
	"""Whether a preference or stay request says something a room can be checked against."""
	if row.get("room_feature"):
		return True
	if row.get("reference_doctype") in ("Hotel Room", "Hotel Amenity") and row.get("reference_name"):
		return True
	if row.get("category") == "Floor" and floor_rule(row.get("value")) is not None:
		return True
	return wants_connecting_room(row)


def validate_matchable(doc) -> None:
	"""Room preferences must name a feature, room, amenity, floor rule or connecting room."""
	if doc.category in ROOM_CATEGORIES and not is_room_matchable(doc):
		frappe.throw(
			_(
				'Say which room feature "{0}" means, so rooms can be matched to it. A floor can also '
				'be written as "High floor", "Low floor" or a floor number.'
			).format(doc.value)
		)
	if doc.priority == "Required" and not is_room_matchable(doc):
		frappe.throw(_("Only preferences that rooms can be matched to can be Required."))
	if (doc.reference_doctype and not doc.reference_name) or (
		doc.reference_name and not doc.reference_doctype
	):
		frappe.throw(_("Pick both what the preference refers to and which one."))


def _clean(fields: dict) -> dict:
	category = fields.get("category")
	if category not in (*ROOM_CATEGORIES, "Dietary", "Service Type", "Provider", "Language", "Other"):
		frappe.throw(_("Pick a category for the preference."))
	value = (fields.get("value") or "").strip()
	if not value and fields.get("room_feature"):
		value = fields["room_feature"]
	if not value and fields.get("reference_name"):
		value = (
			frappe.db.get_value(
				fields["reference_doctype"],
				fields["reference_name"],
				_title_field(fields["reference_doctype"]),
			)
			or fields["reference_name"]
		)
	if not value:
		frappe.throw(_("Say what the guest asked for."))
	priority = fields.get("priority") or "Normal"
	if priority not in PRIORITIES:
		frappe.throw(_("Priority is Required, High or Normal."))
	return {
		"category": category,
		"value": value,
		"priority": priority,
		"room_feature": fields.get("room_feature") or None,
		"reference_doctype": fields.get("reference_doctype") or None,
		"reference_name": fields.get("reference_name") or None,
	}


def _title_field(doctype: str) -> str:
	return frappe.get_meta(doctype).get_title_field() or "name"


def label(row) -> str:
	return row.get("value") or row.get("room_feature") or row.get("reference_name") or ""


# --------------------------------------------------------------------------- preferences


def guest_preferences(
	profiles, property_name: str | None = None, include_sensitive: bool | None = None
) -> list[dict]:
	"""Active preferences of the given profiles that apply at `property_name`, Required first."""
	profiles = [profiles] if isinstance(profiles, str) else [p for p in profiles if p]
	if not profiles:
		return []
	if include_sensitive is None:
		include_sensitive = can_see_sensitive()
	filters = {"guest_profile": ["in", profiles], "is_active": 1}
	if not include_sensitive:
		filters["sensitivity"] = ["!=", SENSITIVE]
	rows = frappe.get_all(
		PREFERENCE,
		filters=filters,
		fields=[
			*MATCH_FIELDS,
			"guest_profile",
			"guest_name",
			"source",
			"sensitivity",
			"property",
			"last_confirmed_on",
			"notes",
		],
	)
	rows = [row for row in rows if not row.property or not property_name or row.property == property_name]
	for row in rows:
		row["room_matchable"] = is_room_matchable(row)
		row["sensitive"] = row.sensitivity == SENSITIVE
	return sorted(rows, key=lambda row: (PRIORITIES.index(row.priority or "Normal"), row.category, row.value))


def find_preference(guest_profile: str, fields: dict) -> str | None:
	"""An active preference of the guest that already says the same thing."""
	for row in frappe.get_all(
		PREFERENCE,
		filters={"guest_profile": guest_profile, "is_active": 1, "category": fields["category"]},
		fields=MATCH_FIELDS,
	):
		if _same(row, fields):
			return row.name
	return None


def _same(row, fields: dict) -> bool:
	if fields.get("reference_name") or row.get("reference_name"):
		return (row.get("reference_doctype"), row.get("reference_name")) == (
			fields.get("reference_doctype"),
			fields.get("reference_name"),
		)
	if fields.get("room_feature") or row.get("room_feature"):
		return row.get("room_feature") == fields.get("room_feature")
	return (row.get("value") or "").strip().lower() == (fields.get("value") or "").strip().lower()


def add_preference(
	guest_profile: str,
	category: str,
	value: str | None = None,
	priority: str = "Normal",
	room_feature: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	sensitivity: str = "Normal",
	property_name: str | None = None,
	source: str = "Guest stated",
	notes: str | None = None,
	consent_basis: str | None = None,
) -> str:
	"""Save a preference to the guest's profile, or reconfirm the one that already says it."""
	_require_edit()
	if not frappe.db.exists("Guest Profile", guest_profile):
		raise frappe.DoesNotExistError(_("Guest Profile {0} does not exist.").format(guest_profile))
	if sensitivity == SENSITIVE and not can_see_sensitive():
		raise frappe.PermissionError(_("You are not allowed to record sensitive preferences."))
	fields = _clean(
		{
			"category": category,
			"value": value,
			"priority": priority,
			"room_feature": room_feature,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		}
	)
	existing = find_preference(guest_profile, fields)
	if existing:
		doc = frappe.get_doc(PREFERENCE, existing)
		doc.priority = fields["priority"]
		doc.last_confirmed_on = today()
		if sensitivity == SENSITIVE:
			doc.sensitivity = SENSITIVE
		doc.save(ignore_permissions=True)
		return doc.name
	doc = frappe.get_doc(
		{
			"doctype": PREFERENCE,
			"guest_profile": guest_profile,
			**fields,
			"sensitivity": sensitivity or "Normal",
			"property": property_name or None,
			"source": source,
			"last_confirmed_on": today(),
			"notes": notes,
			"consent_basis": consent_basis,
			"is_active": 1,
		}
	).insert(ignore_permissions=True)
	log_event(
		"Guest Profile",
		guest_profile,
		"Preference Saved",
		data={"preference": doc.name, "category": doc.category, "source": source},
		property_name=property_name,
	)
	return doc.name


def retire_preference(name: str, reason: str | None = None) -> None:
	"""The guest no longer wants it. Kept for history, no longer used."""
	_require_edit()
	doc = frappe.get_doc(PREFERENCE, name)
	if doc.sensitivity == SENSITIVE and not can_see_sensitive():
		raise frappe.PermissionError(_("You are not allowed to change sensitive preferences."))
	if not doc.is_active:
		return
	doc.is_active = 0
	if reason:
		doc.notes = "\n".join(text for text in (doc.notes, reason.strip()) if text)
	doc.save(ignore_permissions=True)
	log_event(
		"Guest Profile", doc.guest_profile, "Preference Retired", reason=reason, data={"preference": name}
	)


# --------------------------------------------------------------------------- stay requests


def stay_requests(stay_name: str, include_closed: bool = False) -> list[dict]:
	filters = {"stay_reservation": stay_name}
	if not include_closed:
		filters["status"] = OPEN
	rows = frappe.get_all(
		REQUEST,
		filters=filters,
		fields=[*MATCH_FIELDS, "status", "source", "suggestion_key", "guest_profile", "notes"],
		order_by="creation asc",
	)
	for row in rows:
		row["room_matchable"] = is_room_matchable(row)
	return rows


def add_stay_request(
	stay_name: str,
	category: str,
	value: str | None = None,
	priority: str = "Normal",
	room_feature: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	notes: str | None = None,
	source: str = "Guest stated",
	suggestion_key: str | None = None,
	guest_profile: str | None = None,
) -> str:
	"""Record something asked for this stay. An open request that says the same is returned."""
	_require_edit()
	stay = frappe.db.get_value(
		"Stay Reservation", stay_name, ["name", "property", "lead_guest", "status"], as_dict=True
	)
	if not stay:
		raise frappe.DoesNotExistError(_("Stay {0} does not exist.").format(stay_name))
	if stay.status in ("Checked Out", "Cancelled", "No Show", "Expired"):
		frappe.throw(_("Stay {0} is {1}; it takes no more requests.").format(stay.name, _(stay.status)))
	fields = _clean(
		{
			"category": category,
			"value": value,
			"priority": priority,
			"room_feature": room_feature,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		}
	)
	for row in stay_requests(stay.name):
		if (suggestion_key and row.suggestion_key == suggestion_key) or (
			row.category == fields["category"] and _same(row, fields)
		):
			return row.name
	doc = frappe.get_doc(
		{
			"doctype": REQUEST,
			"property": stay.property,
			"stay_reservation": stay.name,
			"guest_profile": guest_profile or stay.lead_guest,
			"status": OPEN,
			"source": source,
			"suggestion_key": suggestion_key,
			"notes": notes,
			**fields,
		}
	)
	doc.flags[SERVICE_FLAG] = True
	validate_matchable(doc)
	doc.insert(ignore_permissions=True)
	log_event(
		"Stay Reservation",
		stay.name,
		"Stay Request Added",
		data={"request": doc.name, "category": doc.category, "value": doc.value, "source": source},
	)
	return doc.name


def close_stay_request(name: str, status: str = "Done", notes: str | None = None) -> None:
	"""Mark a request done (the room was set up, the transfer booked) or cancel it."""
	_require_edit()
	if status not in CLOSED_STATUSES:
		frappe.throw(_("A request is closed as Done or Cancelled."))
	doc = frappe.get_doc(REQUEST, name)
	if doc.status != OPEN:
		return
	doc.status = status
	doc.closed_by = frappe.session.user
	doc.closed_at = now_datetime()
	if notes:
		doc.notes = "\n".join(text for text in (doc.notes, notes.strip()) if text)
	doc.flags[SERVICE_FLAG] = True
	doc.save(ignore_permissions=True)
	log_event(
		"Stay Reservation",
		doc.stay_reservation,
		"Stay Request Closed",
		to_status=status,
		reason=notes,
		data={"request": name},
	)


def copy_request_to_profile(name: str, sensitivity: str = "Normal") -> str:
	"""Keep a this-stay request on the guest's profile for every stay. An explicit decision."""
	doc = frappe.get_doc(REQUEST, name)
	if not doc.guest_profile:
		frappe.throw(_("The request has no guest to save it for."))
	return add_preference(
		doc.guest_profile,
		doc.category,
		doc.value,
		priority=doc.priority,
		room_feature=doc.room_feature,
		reference_doctype=doc.reference_doctype,
		reference_name=doc.reference_name,
		sensitivity=sensitivity,
		source="Staff confirmed",
	)


def room_feature_options() -> list[dict]:
	"""Active room features for the preference form, grouped by category."""
	return frappe.get_all(
		"Hotel Room Feature",
		filters={"is_active": 1},
		fields=["name", "category"],
		order_by="category asc, name asc",
	)
