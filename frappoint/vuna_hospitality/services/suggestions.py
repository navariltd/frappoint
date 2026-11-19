"""Suggestions from a guest's history, and what staff did with them (design §19.3, §30.20; plan F18).

When a returning guest is chosen, staff see their **declared** preferences first, then
**observed** suggestions with the evidence behind them: "Deep Tissue Massage: 3 of the last
4 stays; last 12 May". Nothing observed is ever applied or saved by itself. Staff can:

- apply it to this stay (it becomes a Stay Request),
- save it to the profile (it becomes a Guest Preference, source "Accepted suggestion"), or
- dismiss it.

Each action is recorded as Guest Suggestion Feedback. A dismissal lowers the suggestion's rank
next time; it never deletes history. Suggestions are computed on read and not stored. One appears
only after `suggestion_min_occurrences` qualifying occurrences (Hospitality Settings), and the
panel says "no history yet" rather than showing weak guesses.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, date_diff, getdate, now_datetime, today

from frappoint.vuna_hospitality.services import guest_history, preferences

FEEDBACK = "Guest Suggestion Feedback"
SERVICE_FLAG = "from_suggestions_service"

APPLIED = "Applied to stay"
SAVED = "Saved to profile"
DISMISSED = "Dismissed"
TOP_CHOSEN = "Top-ranked chosen"
OVERRIDDEN = "Overridden"

SERVICE = "Service"
ROOM = "Room"
SERVICE_KEY = "service_type"
ROOM_KEY = "room"
KEY_TYPES = {SERVICE_KEY: (SERVICE, "Service Type"), ROOM_KEY: (ROOM, "Hotel Room")}

DEFAULT_MIN_OCCURRENCES = 2
OCCURRENCE_POINTS = 10
RECENCY_POINTS = 10
RECENCY_DAYS = 365
ACCEPTED_POINTS = 5
DISMISSED_POINTS = 20
MAX_REFERENCES = 5


def enabled() -> bool:
	return bool(cint(frappe.db.get_single_value("Hospitality Settings", "enable_preference_suggestions")))


def min_occurrences() -> int:
	value = cint(frappe.db.get_single_value("Hospitality Settings", "suggestion_min_occurrences"))
	return max(1, value or DEFAULT_MIN_OCCURRENCES)


def make_key(kind: str, name: str) -> str:
	return f"{kind}:{name}"


def parse_key(key: str) -> tuple[str, str, str]:
	"""(suggestion type, DocType, name) of a key such as "service_type:Deep Tissue Massage"."""
	kind, _sep, name = (key or "").partition(":")
	if kind not in KEY_TYPES or not name:
		frappe.throw(_("{0} is not a suggestion.").format(key))
	suggestion_type, doctype = KEY_TYPES[kind]
	if not frappe.db.exists(doctype, name):
		raise frappe.DoesNotExistError(_("{0} {1} does not exist.").format(_(doctype), name))
	return suggestion_type, doctype, name


# --------------------------------------------------------------------------- reading


def guest_insights(
	guest_profile: str, stay_name: str | None = None, property_name: str | None = None
) -> dict:
	"""Declared preferences, this stay's requests, and observed suggestions with evidence."""
	profile = frappe.db.get_value(
		"Guest Profile", guest_profile, ["name", "full_name", "vip_level"], as_dict=True
	)
	if not profile:
		raise frappe.DoesNotExistError(_("Guest Profile {0} does not exist.").format(guest_profile))
	if stay_name and not property_name:
		property_name = frappe.db.get_value("Stay Reservation", stay_name, "property")
	data = {
		"guest_profile": profile.name,
		"guest_name": profile.full_name,
		"vip_level": profile.vip_level,
		"declared": preferences.guest_preferences(profile.name, property_name),
		"requests": preferences.stay_requests(stay_name) if stay_name else [],
		"suggestions_enabled": enabled(),
		"suggestions": [],
		"history": {"stays": 0, "services": 0},
		"min_occurrences": min_occurrences(),
		"can_edit": preferences.can_edit(),
		"can_see_sensitive": preferences.can_see_sensitive(),
	}
	if data["suggestions_enabled"]:
		data.update(observe(profile.name, stay_name, data["declared"], data["requests"]))
	data["no_history"] = data["suggestions_enabled"] and not (
		data["history"]["stays"] or data["history"]["services"]
	)
	return data


def _feedback_counts(guest_profile: str) -> dict:
	counts = {}
	for row in frappe.get_all(
		FEEDBACK,
		filters={"guest_profile": guest_profile, "action": ["in", (APPLIED, SAVED, DISMISSED)]},
		fields=["suggestion_key", "action"],
	):
		entry = counts.setdefault(row.suggestion_key, {"accepted": 0, "dismissed": 0})
		entry["dismissed" if row.action == DISMISSED else "accepted"] += 1
	return counts


def _declared_keys(declared: list[dict]) -> set[str]:
	keys = set()
	for row in declared:
		if row.get("reference_doctype") == "Service Type":
			keys.add(make_key(SERVICE_KEY, row.reference_name))
		elif row.get("reference_doctype") == "Hotel Room":
			keys.add(make_key(ROOM_KEY, row.reference_name))
	return keys


def _recency(last) -> float:
	days = max(0, date_diff(today(), last)) if last else RECENCY_DAYS
	return round(max(0.0, RECENCY_POINTS * (1 - days / RECENCY_DAYS)), 2)


def _evidence(in_stays: int, of_stays: int, visits: int, last) -> str:
	parts = []
	if in_stays:
		parts.append(
			_("{0} of the last {1} stays").format(in_stays, of_stays)
			if of_stays != 1
			else _("on the last stay")
		)
	if visits:
		parts.append(
			_("{0} visits outside a stay").format(visits) if visits != 1 else _("1 visit outside a stay")
		)
	if last:
		parts.append(_("last {0}").format(frappe.format(getdate(last), {"fieldtype": "Date"})))
	return "; ".join(parts)


def observe(
	guest_profile: str,
	stay_name: str | None = None,
	declared: list[dict] | None = None,
	requests: list[dict] | None = None,
) -> dict:
	"""Observed suggestions, best first, and how much history there was to look at."""
	stays = guest_history.completed_stays(guest_profile)
	stay_names = {stay.name for stay in stays}
	services = guest_history.service_occurrences(guest_profile)
	rooms = guest_history.room_occurrences(guest_profile, stays)
	feedback = _feedback_counts(guest_profile)
	declared_keys = _declared_keys(declared or [])
	applied_keys = {row.get("suggestion_key") for row in (requests or []) if row.get("suggestion_key")}
	threshold = min_occurrences()

	found = []
	by_service: dict[str, list[dict]] = {}
	for row in services:
		# A stay older than the look-back window, or not finished yet, doesn't count.
		if row["stay"] and row["stay"] not in stay_names:
			continue
		if row["service_type"]:
			by_service.setdefault(row["service_type"], []).append(row)
	for service_type, rows in by_service.items():
		in_stays = {row["stay"] for row in rows if row["stay"]}
		visits = [row for row in rows if not row["stay"]]
		dates = [getdate(row["date"]) for row in rows if row["date"]]
		found.append(
			_suggestion(
				SERVICE_KEY,
				service_type,
				service_type,
				len(in_stays),
				len(stays),
				len(visits),
				max(dates) if dates else None,
				[row["appointment"] for row in rows],
			)
		)
	by_room: dict[str, list[dict]] = {}
	for row in rooms:
		by_room.setdefault(row["room"], []).append(row)
	for room, rows in by_room.items():
		in_stays = {row["stay"] for row in rows}
		found.append(
			_suggestion(
				ROOM_KEY,
				room,
				_("Room {0}").format(rows[0]["room_number"]),
				len(in_stays),
				len(stays),
				0,
				max(getdate(row["date"]) for row in rows),
				sorted(in_stays),
			)
		)

	suggestions = []
	for item in found:
		if item["occurrences"] < threshold or item["key"] in declared_keys:
			continue
		counts = feedback.get(item["key"], {"accepted": 0, "dismissed": 0})
		item["dismissed"] = counts["dismissed"]
		item["score"] = round(
			item["score"] + ACCEPTED_POINTS * counts["accepted"] - DISMISSED_POINTS * counts["dismissed"], 2
		)
		item["applied_to_stay"] = item["key"] in applied_keys
		suggestions.append(item)
	suggestions.sort(key=lambda item: (-item["score"], item["title"]))
	return {
		"suggestions": suggestions,
		"history": {"stays": len(stays), "services": len(services)},
	}


def _suggestion(kind, name, title, in_stays, of_stays, visits, last, references) -> dict:
	suggestion_type, doctype = KEY_TYPES[kind]
	occurrences = in_stays + visits
	return {
		"key": make_key(kind, name),
		"type": suggestion_type,
		"reference_doctype": doctype,
		"reference_name": name,
		"title": title,
		"observed": True,
		"occurrences": occurrences,
		"in_stays": in_stays,
		"of_stays": of_stays,
		"visits": visits,
		"last_date": str(last) if last else None,
		"evidence": _evidence(in_stays, of_stays, visits, last),
		"references": references[:MAX_REFERENCES],
		"score": OCCURRENCE_POINTS * occurrences + _recency(last),
	}


# --------------------------------------------------------------------------- acting


def record_feedback(
	guest_profile: str,
	suggestion_type: str,
	suggestion_key: str,
	action: str,
	stay_name: str | None = None,
	property_name: str | None = None,
	evidence=None,
	**room_choice,
) -> str:
	"""Log what staff did. `room_choice` holds top_ranked_room, chosen_room, chosen_rank, reason."""
	if stay_name and not property_name:
		property_name = frappe.db.get_value("Stay Reservation", stay_name, "property")
	if evidence is not None and not isinstance(evidence, str):
		evidence = json.dumps(evidence, default=str, sort_keys=True)
	doc = frappe.get_doc(
		{
			"doctype": FEEDBACK,
			"guest_profile": guest_profile,
			"suggestion_type": suggestion_type,
			"suggestion_key": suggestion_key,
			"action": action,
			"stay_reservation": stay_name,
			"property": property_name,
			"evidence": evidence,
			"acted_by": frappe.session.user,
			"acted_on": now_datetime(),
			**room_choice,
		}
	)
	doc.flags[SERVICE_FLAG] = True
	doc.insert(ignore_permissions=True)
	return doc.name


def _require_enabled() -> None:
	if not enabled():
		frappe.throw(_("Preference suggestions are switched off in Hospitality Settings."))


def _request_fields(suggestion_type: str, name: str) -> dict:
	if suggestion_type == ROOM:
		return {"category": "Room", "reference_doctype": "Hotel Room", "reference_name": name}
	return {"category": "Service Type", "reference_doctype": "Service Type", "reference_name": name}


def apply_to_stay(stay_name: str, key: str, evidence: str | None = None) -> str:
	"""Use a suggestion for this stay only: it becomes an open Stay Request. Nothing is booked."""
	_require_enabled()
	suggestion_type, _doctype, name = parse_key(key)
	stay = frappe.db.get_value(
		"Stay Reservation", stay_name, ["name", "lead_guest", "property"], as_dict=True
	)
	if not stay:
		raise frappe.DoesNotExistError(_("Stay {0} does not exist.").format(stay_name))
	if not stay.lead_guest:
		frappe.throw(_("The stay has no guest profile yet."))
	request = preferences.add_stay_request(
		stay.name,
		**_request_fields(suggestion_type, name),
		source="Applied suggestion",
		suggestion_key=key,
		notes=evidence,
	)
	record_feedback(stay.lead_guest, suggestion_type, key, APPLIED, stay.name, stay.property, evidence)
	return request


def save_to_profile(
	guest_profile: str, key: str, evidence: str | None = None, stay_name: str | None = None
) -> str:
	"""Keep a suggestion as a declared preference: it applies to every stay from now on."""
	_require_enabled()
	suggestion_type, _doctype, name = parse_key(key)
	preference = preferences.add_preference(
		guest_profile,
		**_request_fields(suggestion_type, name),
		source="Accepted suggestion",
		notes=evidence,
	)
	record_feedback(guest_profile, suggestion_type, key, SAVED, stay_name, evidence=evidence)
	return preference


def dismiss(guest_profile: str, key: str, evidence: str | None = None, stay_name: str | None = None) -> str:
	"""Not useful: rank it lower next time. The history behind it is untouched."""
	_require_enabled()
	if not preferences.can_edit():
		raise frappe.PermissionError(_("You are not allowed to dismiss suggestions."))
	suggestion_type, _doctype, _name = parse_key(key)
	return record_feedback(guest_profile, suggestion_type, key, DISMISSED, stay_name, evidence=evidence)
