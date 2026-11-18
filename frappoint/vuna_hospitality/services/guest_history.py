"""What a guest actually did on earlier visits, for suggestions (design §19.3, §29; plan F18).

History counts only what the guest **consumed** and **completed**:

- Services: Service Participants (F15) where the profile was the participant, on an appointment
  that was completed, not refunded, and whose folio charge wasn't reversed. A guest who only paid
  for or booked someone else's treatment is never the participant, so it never counts for them.
- Legacy appointments, booked before the hotel went live, count once a guest row on the
  appointment is matched to the profile and staff confirm the match (Guest History Match).
- Rooms: the rooms of completed stays where the profile was a guest, except a room the guest was
  moved out of for noise or maintenance.

Matching is conservative: an appointment guest is proposed for a profile only when their email
or phone identifies exactly one profile, and nothing counts until a person confirms it.
"""

import re

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from frappoint.vuna_hospitality.constants import (
	DATA_PROTECTION_OFFICER,
	FRONT_DESK_MANAGER,
	GUEST_SERVICES_AGENT,
	HOSPITALITY_MANAGER,
)
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.feature_flag import hospitality_job
from frappoint.vuna_hospitality.services.guests import phone_key

MATCH = "Guest History Match"
PARTICIPANT = "Service Participant"
APPOINTMENT = "Service Appointment"
APPOINTMENT_GUEST = "Service Appointment Guest"
SERVICE_FLAG = "from_guest_history"

PROPOSED = "Proposed"
CONFIRMED = "Confirmed"
REJECTED = "Rejected"

COMPLETED_APPOINTMENTS = ("Completed", "Closed")
REFUNDED_PAYMENTS = ("Refunded", "Partly Refunded")
UNCONSUMED_PARTICIPANTS = ("Cancelled", "No Show", "Failed")
GONE_STAY_GUESTS = ("Did Not Stay", "Removed")
COMPLETED_STAY = "Checked Out"
# A guest moved out of a room for these reasons didn't like it; that room isn't suggested again.
COMPLAINT_MOVE_REASONS = ("Noise", "Maintenance")

LOOKBACK_STAYS = 10
MATCH_BATCH = 500

REVIEW_ROLES = (
	"System Manager",
	HOSPITALITY_MANAGER,
	FRONT_DESK_MANAGER,
	GUEST_SERVICES_AGENT,
	DATA_PROTECTION_OFFICER,
)


def can_review(user: str | None = None) -> bool:
	return bool(set(REVIEW_ROLES) & set(frappe.get_roles(user)))


# --------------------------------------------------------------------------- stays


def completed_stays(guest_profile: str, limit: int = LOOKBACK_STAYS) -> list[dict]:
	"""The guest's most recent checked-out stays, newest first."""
	stay_names = frappe.get_all(
		"Stay Guest",
		filters={"guest_profile": guest_profile, "status": ["not in", GONE_STAY_GUESTS]},
		pluck="stay_reservation",
	)
	if not stay_names:
		return []
	return frappe.get_all(
		"Stay Reservation",
		filters={"name": ["in", list(set(stay_names))], "status": COMPLETED_STAY},
		fields=["name", "property", "arrival_date", "departure_date"],
		order_by="departure_date desc",
		limit_page_length=limit,
	)


# --------------------------------------------------------------------------- services


def _refunded(appointment) -> bool:
	return appointment.payment_status in REFUNDED_PAYMENTS


def _reversed(folio_transaction: str | None) -> bool:
	return bool(folio_transaction and frappe.db.exists("Folio Transaction", {"reverses": folio_transaction}))


def _appointments(names) -> dict:
	if not names:
		return {}
	return {
		row.name: row
		for row in frappe.get_all(
			APPOINTMENT,
			filters={"name": ["in", list(set(names))]},
			fields=["name", "status", "payment_status", "appointment_type", "appointment_date"],
		)
	}


def service_occurrences(guest_profile: str) -> list[dict]:
	"""Each completed service the guest consumed: {service_type, date, stay, appointment, source}."""
	participants = frappe.get_all(
		PARTICIPANT,
		filters={"guest_profile": guest_profile, "status": ["not in", UNCONSUMED_PARTICIPANTS]},
		fields=[
			"name",
			"service_appointment",
			"service_type",
			"appointment_date",
			"stay_reservation",
			"folio_transaction",
		],
	)
	appointments = _appointments([row.service_appointment for row in participants])
	occurrences = []
	for row in participants:
		appointment = appointments.get(row.service_appointment)
		if not appointment or appointment.status not in COMPLETED_APPOINTMENTS:
			continue
		if _refunded(appointment) or _reversed(row.folio_transaction):
			continue
		occurrences.append(
			{
				"service_type": row.service_type or appointment.appointment_type,
				"date": row.appointment_date or appointment.appointment_date,
				"stay": row.stay_reservation,
				"appointment": row.service_appointment,
				"source": "Stay" if row.stay_reservation else "Visit",
			}
		)
	return occurrences + _legacy_occurrences(guest_profile)


def _legacy_occurrences(guest_profile: str) -> list[dict]:
	"""Confirmed matches of appointments booked outside a stay (before go-live, or walk-ins)."""
	appointment_names = frappe.get_all(
		MATCH,
		filters={"guest_profile": guest_profile, "status": CONFIRMED},
		pluck="service_appointment",
	)
	occurrences = []
	for appointment in _appointments(appointment_names).values():
		if appointment.status not in COMPLETED_APPOINTMENTS or _refunded(appointment):
			continue
		# Appointments charged to a stay are attributed by their participants instead.
		if frappe.db.exists(PARTICIPANT, {"service_appointment": appointment.name}):
			continue
		occurrences.append(
			{
				"service_type": appointment.appointment_type,
				"date": appointment.appointment_date,
				"stay": None,
				"appointment": appointment.name,
				"source": "Visit",
			}
		)
	return occurrences


# --------------------------------------------------------------------------- rooms


def room_occurrences(guest_profile: str, stays: list[dict] | None = None) -> list[dict]:
	"""The rooms of the guest's completed stays: {room, room_number, floor, stay, date}."""
	stays = completed_stays(guest_profile) if stays is None else stays
	if not stays:
		return []
	segments = frappe.get_all(
		"Room Assignment",
		filters={"stay_reservation": ["in", [stay["name"] for stay in stays]], "status": "Released"},
		fields=["name", "stay_reservation", "hotel_room", "room_number", "end_date"],
	)
	if not segments:
		return []
	complained = set(
		frappe.get_all(
			"Room Assignment",
			filters={
				"previous_assignment": ["in", [segment.name for segment in segments]],
				"move_reason": ["in", COMPLAINT_MOVE_REASONS],
			},
			pluck="previous_assignment",
		)
	)
	floors = dict(
		frappe.get_all(
			"Hotel Room",
			filters={"name": ["in", list({segment.hotel_room for segment in segments})]},
			fields=["name", "floor"],
			as_list=True,
		)
	)
	return [
		{
			"room": segment.hotel_room,
			"room_number": segment.room_number,
			"floor": floors.get(segment.hotel_room),
			"stay": segment.stay_reservation,
			"date": segment.end_date,
		}
		for segment in segments
		if segment.name not in complained
	]


# --------------------------------------------------------------------------- legacy matching


def _email(value: str | None) -> str | None:
	value = (value or "").strip().lower()
	return value if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value) else None


def _profiles_by_contact() -> tuple[dict, dict]:
	"""Active, named profiles indexed by email and by phone key; a key shared by two is dropped."""
	by_email, by_phone = {}, {}
	for row in frappe.get_all(
		"Guest Profile",
		filters={"merged_into": ["is", "not set"], "is_provisional": 0},
		fields=["name", "email", "mobile_no"],
	):
		for index, key in ((by_email, _email(row.email)), (by_phone, phone_key(row.mobile_no))):
			if key:
				index.setdefault(key, set()).add(row.name)
	return by_email, by_phone


def _candidate(row, by_email: dict, by_phone: dict) -> tuple[str, str] | None:
	"""The one profile this appointment guest's email or phone points to, and what matched."""
	from_email = by_email.get(_email(row.email), set())
	from_phone = by_phone.get(phone_key(row.mobile_no), set())
	found = from_email | from_phone
	if len(found) != 1 or len(from_email) > 1 or len(from_phone) > 1:
		return None
	profile = next(iter(found))
	if from_email and from_phone:
		return profile, "Email and Phone"
	return profile, "Email" if from_email else "Phone"


@hospitality_job
def propose_matches(limit: int = MATCH_BATCH) -> int:
	"""Propose Guest Profiles for guests on completed appointments. Staff confirm each one."""
	limit = max(1, cint(limit) or MATCH_BATCH)
	by_email, by_phone = _profiles_by_contact()
	if not by_email and not by_phone:
		return 0
	known = set(frappe.get_all(MATCH, pluck="guest_row"))
	guest_rows = frappe.get_all(
		APPOINTMENT_GUEST,
		filters={"parenttype": APPOINTMENT},
		fields=["name", "parent", "full_name", "email", "mobile_no"],
		order_by="creation desc",
		limit_page_length=limit * 5,
	)
	appointments = _appointments([row.parent for row in guest_rows if row.name not in known])
	attributed = set(
		frappe.get_all(
			PARTICIPANT,
			filters={"service_appointment": ["in", list(appointments) or [""]]},
			pluck="service_appointment",
		)
	)
	created = 0
	for row in guest_rows:
		appointment = appointments.get(row.parent)
		if row.name in known or not appointment or row.parent in attributed:
			continue
		if appointment.status not in COMPLETED_APPOINTMENTS:
			continue
		candidate = _candidate(row, by_email, by_phone)
		if not candidate:
			continue
		doc = frappe.get_doc(
			{
				"doctype": MATCH,
				"status": PROPOSED,
				"guest_profile": candidate[0],
				"match_basis": candidate[1],
				"service_appointment": row.parent,
				"guest_row": row.name,
				"appointment_date": appointment.appointment_date,
				"service_type": appointment.appointment_type,
				"guest_name": row.full_name,
				"email": row.email,
				"mobile_no": row.mobile_no,
			}
		)
		doc.flags[SERVICE_FLAG] = True
		doc.insert(ignore_permissions=True)
		created += 1
		if created >= limit:
			break
	return created


def proposed_matches(limit: int = 100) -> list[dict]:
	"""The review queue: proposed matches, with what each matched on."""
	return frappe.get_all(
		MATCH,
		filters={"status": PROPOSED},
		fields=[
			"name",
			"guest_profile",
			"profile_name",
			"match_basis",
			"service_appointment",
			"appointment_date",
			"service_type",
			"guest_name",
			"email",
			"mobile_no",
		],
		order_by="appointment_date desc, creation desc",
		limit_page_length=max(1, min(cint(limit) or 100, 500)),
	)


def review_match(name: str, confirm: bool) -> None:
	"""Confirm (the history now counts for the profile) or reject a proposed match."""
	if not can_review():
		raise frappe.PermissionError(_("You are not allowed to review guest history matches."))
	doc = frappe.get_doc(MATCH, name)
	if doc.status != PROPOSED:
		frappe.throw(_("This match was already {0}.").format(_(doc.status).lower()))
	doc.status = CONFIRMED if confirm else REJECTED
	doc.reviewed_by = frappe.session.user
	doc.reviewed_on = now_datetime()
	doc.flags[SERVICE_FLAG] = True
	doc.save(ignore_permissions=True)
	log_event(
		"Guest Profile",
		doc.guest_profile,
		"Guest History Matched" if confirm else "Guest History Match Rejected",
		data={"match": doc.name, "appointment": doc.service_appointment, "basis": doc.match_basis},
	)
