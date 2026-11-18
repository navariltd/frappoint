"""Rooms ranked for a guest when staff assign one (design §19.4; plan F18).

1. **Eligible rooms** pass the hard rules first: the stay's room type, free for the whole stay
   (the same overlap check assignment uses), in service, and big enough. Preferences never
   override these.
2. **Required** preferences (step-free access, say) remove rooms that don't meet them. Staff can
   still pick such a room, but only with a reason.
3. The rest **score** points for each declared preference and this-stay request they meet
   (weighted by priority) and for the guest's own history: the same room, or the same floor, on
   earlier stays. Declared preferences weigh more than history.
4. **Ties** go to the room that is ready now, then the housekeeping zone with fewer arrivals that
   day, then the room number.
5. Each room **explains** itself: matched and missed preferences.
6. When staff **confirm**, the choice, the top-ranked room and whether they differed are logged as
   Guest Suggestion Feedback.

Ranking runs when it's asked for and holds no locks; assignment still takes its usual lock and
overlap check. Sensitive preferences rank rooms only for roles allowed to see them, so they never
appear in another role's explanation.
"""

import frappe
from frappe import _
from frappe.utils import cint

from frappoint.vuna_hospitality.services import front_desk, guest_history, preferences, suggestions
from frappoint.vuna_hospitality.services.event_log import log_event

STAY = "Stay Reservation"
ROOM = "Hotel Room"

PRIORITY_POINTS = {"Required": 40, "High": 30, "Normal": 10}
SAME_ROOM_POINTS = 6
SAME_FLOOR_POINTS = 2
MAX_HISTORY_STAYS = 3

DECLARED = "Declared"
THIS_STAY = "This stay"


class PreferenceRequiredError(frappe.ValidationError):
	"""The room misses a preference the guest requires, and no override reason was given."""


def enabled() -> bool:
	return bool(cint(frappe.db.get_single_value("Hospitality Settings", "enable_preference_room_ranking")))


# --------------------------------------------------------------------------- rules


def _stay_profiles(stay) -> list[str]:
	"""The lead guest first, then every other guest still on the stay."""
	profiles = [stay.lead_guest] if stay.lead_guest else []
	for profile in frappe.get_all(
		"Stay Guest",
		filters={
			"stay_reservation": stay.name,
			"status": ["in", front_desk.ACTIVE_GUEST_STATUSES],
			"guest_profile": ["is", "set"],
		},
		pluck="guest_profile",
	):
		if profile not in profiles:
			profiles.append(profile)
	return profiles


def ranking_rules(stay, include_sensitive: bool | None = None) -> list[dict]:
	"""Room-matchable preferences of the stay's guests, and the stay's own open requests."""
	rules = []
	for row in preferences.guest_preferences(_stay_profiles(stay), stay.property, include_sensitive):
		if row.room_matchable:
			rules.append({**row, "origin": DECLARED})
	for row in preferences.stay_requests(stay.name):
		if row.room_matchable:
			rules.append({**row, "origin": THIS_STAY, "sensitive": False})
	# Two guests (or a profile and this stay) asking for the same thing count once, at the
	# higher priority.
	unique: dict[tuple, dict] = {}
	for rule in rules:
		key = (rule.get("room_feature"), rule.get("reference_doctype"), rule.get("reference_name"))
		if not any(key):
			key = (rule["category"], (rule.get("value") or "").lower())
		kept = unique.get(key)
		if not kept or PRIORITY_POINTS[rule["priority"]] > PRIORITY_POINTS[kept["priority"]]:
			unique[key] = rule
	return sorted(
		unique.values(), key=lambda rule: (-PRIORITY_POINTS[rule["priority"]], preferences.label(rule))
	)


def _floor_middle(property_name: str) -> float | None:
	floors = [
		floor
		for floor in frappe.get_all(ROOM, filters={"property": property_name, "is_active": 1}, pluck="floor")
		if floor is not None
	]
	if len(set(floors)) < 2:
		return None
	return (min(floors) + max(floors)) / 2


def meets(rule: dict, room: dict, amenities: set[str], floor_middle: float | None) -> bool:
	"""Whether `room` gives the guest what `rule` asks for."""
	if rule.get("room_feature"):
		return rule["room_feature"] in room["features"]
	if rule.get("reference_doctype") == ROOM:
		return room["name"] == rule.get("reference_name")
	if rule.get("reference_doctype") == "Hotel Amenity":
		return rule.get("reference_name") in amenities
	if rule.get("category") == "Floor":
		wanted = preferences.floor_rule(rule.get("value"))
		floor = room.get("floor")
		if isinstance(wanted, int):
			return floor == wanted
		if floor is None or floor_middle is None:
			return False
		return floor > floor_middle if wanted == preferences.HIGH_FLOOR else floor < floor_middle
	if preferences.wants_connecting_room(rule):
		return bool(room.get("connecting_room"))
	return False


# --------------------------------------------------------------------------- ranking


def _room_details(names: list[str]) -> dict:
	details = {
		row.name: {**row, "features": set()}
		for row in frappe.get_all(
			ROOM,
			filters={"name": ["in", names or [""]]},
			fields=["name", "connecting_room", "housekeeping_zone", "capacity_override", "building"],
		)
	}
	for row in frappe.get_all(
		"Hotel Room Feature Item",
		filters={"parenttype": ROOM, "parent": ["in", names or [""]]},
		fields=["parent", "feature"],
	):
		details[row.parent]["features"].add(row.feature)
	return details


def _zone_arrivals(stay) -> dict:
	"""How many rooms in each housekeeping zone already take an arrival on the stay's arrival day."""
	rooms = frappe.get_all(
		"Room Assignment",
		filters={
			"property": stay.property,
			"status": "Assigned",
			"start_date": stay.arrival_date,
			"stay_reservation": ["!=", stay.name],
		},
		pluck="hotel_room",
	)
	counts: dict[str, int] = {}
	for zone in frappe.get_all(ROOM, filters={"name": ["in", rooms or [""]]}, pluck="housekeeping_zone"):
		counts[zone or ""] = counts.get(zone or "", 0) + 1
	return counts


def _history(stay) -> tuple[dict, dict]:
	"""Earlier stays of the lead guest per room and per floor (rooms they complained about excluded)."""
	if not stay.lead_guest:
		return {}, {}
	per_room: dict[str, set] = {}
	per_floor: dict[int, set] = {}
	for row in guest_history.room_occurrences(stay.lead_guest):
		if row["stay"] == stay.name:
			continue
		per_room.setdefault(row["room"], set()).add(row["stay"])
		if row["floor"] is not None:
			per_floor.setdefault(row["floor"], set()).add(row["stay"])
	return {room: len(stays) for room, stays in per_room.items()}, {
		floor: len(stays) for floor, stays in per_floor.items()
	}


def rank_rooms(stay_name: str) -> dict:
	"""The stay's candidate rooms, best first, each with why it ranks where it does."""
	stay = frappe.get_doc(STAY, stay_name)
	rooms = front_desk.get_assignable_rooms(stay_name)
	result = {
		"enabled": enabled(),
		"rooms": rooms,
		"rules": [],
		"top_room": None,
		"personalised": False,
		"no_room_meets_required": False,
	}
	if not result["enabled"]:
		for room in rooms:
			room.update(eligible=bool(room["available"]), rank=None, matched=[], missed=[], excluded=[])
		return result

	rules = ranking_rules(stay)
	details = _room_details([room["name"] for room in rooms])
	amenities = set(
		frappe.get_all(
			"Room Type Amenity",
			filters={"parenttype": "Room Type", "parent": stay.room_type},
			pluck="amenity",
		)
	)
	floor_middle = _floor_middle(stay.property)
	zones = _zone_arrivals(stay)
	same_room, same_floor = _history(stay)
	# "Same floor as before" says nothing when every candidate room is on one floor.
	if len({room.get("floor") for room in rooms}) < 2:
		same_floor = {}
	party = cint(stay.adults) + cint(stay.children)

	for room in rooms:
		room.update(details.get(room["name"], {"features": set()}))
		blocked = [room["unavailable_reason"]] if not room["available"] else []
		capacity = cint(room.get("capacity_override"))
		if capacity and capacity < party:
			blocked.append(_("Sleeps {0}").format(capacity))
		matched, missed, required_missed, score = [], [], [], 0
		for rule in rules:
			text = preferences.label(rule)
			if meets(rule, room, amenities, floor_middle):
				matched.append(text)
				score += PRIORITY_POINTS[rule["priority"]]
			else:
				missed.append(text)
				if rule["priority"] == "Required":
					required_missed.append(text)
		stays_here = same_room.get(room["name"], 0)
		if stays_here:
			matched.append(
				_("Stayed here before") if stays_here == 1 else _("Stayed here {0} times").format(stays_here)
			)
			score += SAME_ROOM_POINTS * min(stays_here, MAX_HISTORY_STAYS)
		floor_stays = same_floor.get(room.get("floor"), 0) - stays_here
		if floor_stays > 0:
			matched.append(_("Same floor as before"))
			score += SAME_FLOOR_POINTS * min(floor_stays, MAX_HISTORY_STAYS)
		room.update(
			score=score,
			matched=matched,
			missed=missed,
			required_missed=required_missed,
			blocked=blocked,
			excluded=blocked + [_("No {0}").format(text) for text in required_missed],
			eligible=not blocked and not required_missed,
			zone_arrivals=zones.get(room.get("housekeeping_zone") or "", 0),
			rank=None,
		)
		room["features"] = sorted(room["features"])

	ranked = sorted(
		(room for room in rooms if room["eligible"]),
		key=lambda room: (
			-room["score"],
			not room["ready"],
			room["zone_arrivals"],
			room["room_number"],
		),
	)
	for rank, room in enumerate(ranked, start=1):
		room["rank"] = rank
	others = sorted(
		(room for room in rooms if not room["eligible"]),
		key=lambda room: (bool(room["blocked"]), room["room_number"]),
	)
	result.update(
		rooms=ranked + others,
		rules=[
			{
				"label": preferences.label(rule),
				"priority": rule["priority"],
				"origin": rule["origin"],
				"sensitive": bool(rule.get("sensitive")),
			}
			for rule in rules
		],
		top_room=ranked[0]["name"] if ranked else None,
		personalised=bool(rules or same_room or same_floor),
		no_room_meets_required=not ranked
		and any(room["required_missed"] and not room["blocked"] for room in rooms),
	)
	return result


# --------------------------------------------------------------------------- choosing


def _entry(ranking: dict | None, room: str) -> dict | None:
	if not ranking or not ranking["enabled"]:
		return None
	return next((row for row in ranking["rooms"] if row["name"] == room), None)


def _check_choice(ranking: dict | None, room: str, override_reason: str | None) -> None:
	entry = _entry(ranking, room)
	if entry and entry.get("required_missed") and not (override_reason or "").strip():
		raise PreferenceRequiredError(
			_(
				"Room {0} doesn't have {1}, which the guest requires. Pick another room, or give a "
				"reason to use this one."
			).format(entry["room_number"], ", ".join(entry["required_missed"]))
		)


def _record_choice(stay_name: str, room: str, ranking: dict | None, override_reason: str | None) -> None:
	entry = _entry(ranking, room)
	stay = frappe.db.get_value(STAY, stay_name, ["name", "lead_guest", "property"], as_dict=True)
	# Without preferences or history the order is only readiness and room number: nothing to learn.
	if not entry or not stay.lead_guest or not ranking["personalised"]:
		return
	top = next((row for row in ranking["rooms"] if row["name"] == ranking["top_room"]), None)
	overridden = room != ranking["top_room"] or bool(entry.get("required_missed"))
	reason = (override_reason or "").strip() or None
	suggestions.record_feedback(
		stay.lead_guest,
		suggestions.ROOM,
		suggestions.make_key(suggestions.ROOM_KEY, room),
		suggestions.OVERRIDDEN if overridden else suggestions.TOP_CHOSEN,
		stay.name,
		stay.property,
		evidence={
			"rules": [rule["label"] for rule in ranking["rules"]],
			"top": top and {"room": top["room_number"], "matched": top["matched"], "missed": top["missed"]},
			"chosen": {"room": entry["room_number"], "matched": entry["matched"], "missed": entry["missed"]},
		},
		top_ranked_room=ranking["top_room"],
		chosen_room=room,
		chosen_rank=entry.get("rank") or 0,
		reason=reason,
	)
	if entry.get("required_missed"):
		log_event(
			STAY,
			stay.name,
			"Required Preference Overridden",
			reason=reason,
			data={"room": entry["room_number"], "missed": entry["required_missed"]},
		)


def assign_ranked(stay_name: str, room: str, lock: bool = False, override_reason: str | None = None) -> str:
	"""Assign a room the way the ranked list offers it, and log how the choice compared."""
	ranking = rank_rooms(stay_name) if enabled() else None
	_check_choice(ranking, room, override_reason)
	assignment = front_desk.assign_room(stay_name, room, lock=lock)
	_record_choice(stay_name, room, ranking, override_reason)
	return assignment


def move_ranked(
	stay_name: str,
	room: str,
	move_reason: str,
	notes: str | None = None,
	override_reason: str | None = None,
) -> str:
	"""Move an in-house stay, with the same preference check and log as assigning."""
	ranking = rank_rooms(stay_name) if enabled() else None
	_check_choice(ranking, room, override_reason)
	assignment = front_desk.move_room(stay_name, room, move_reason, notes)
	_record_choice(stay_name, room, ranking, override_reason)
	return assignment
