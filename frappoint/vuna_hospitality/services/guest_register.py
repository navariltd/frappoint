"""The statutory guest register (design §25.3; plan F20).

At check-in, each registering guest (every adult) gets a **Guest Register Entry**: a snapshot of
the details the law asks for. A property turns the register on and lists which details it needs,
for residents (the company's country) and for foreign guests; nothing else is collected. Check-in
is refused while a required detail is missing.

The entry is a snapshot: it keeps the statutory record for the statutory period even if the
profile is later changed or anonymized. The document number is stored encrypted and shown masked;
revealing it, and exporting the register, are recorded in the event log.
"""

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime

from frappoint.vuna_hospitality.constants import (
	DATA_PROTECTION_OFFICER,
	FRONT_DESK_MANAGER,
	HOSPITALITY_MANAGER,
)
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.guests import mask_document_number

ENTRY = "Guest Register Entry"
PROFILE = "Guest Profile"
STAY = "Stay Reservation"
STAY_GUEST = "Stay Guest"
SERVICE_FLAG = "from_guest_register"

ALL, RESIDENTS, FOREIGN = "All Guests", "Residents", "Foreign Guests"
RESIDENT, FOREIGN_CLASS = "Resident", "Foreign"

NATIONALITY = "Nationality"
ID_DOCUMENT = "ID Document"
DATE_OF_BIRTH = "Date of Birth"
ARRIVED_FROM = "Arrived From"
NEXT_DESTINATION = "Next Destination"
ACCEPTANCE = "Acceptance Reference"

# What a property asks for when it lists nothing itself.
DEFAULT_REQUIREMENTS = {
	RESIDENT: (NATIONALITY, ID_DOCUMENT),
	FOREIGN_CLASS: (NATIONALITY, ID_DOCUMENT, ARRIVED_FROM, NEXT_DESTINATION),
}

# Who may see full document numbers and export the register.
EXPORT_ROLES = ("System Manager", HOSPITALITY_MANAGER, DATA_PROTECTION_OFFICER)
REVEAL_ROLES = (*EXPORT_ROLES, FRONT_DESK_MANAGER)


class RegisterIncompleteError(frappe.ValidationError):
	"""A registering guest is missing a detail the guest register needs."""


def is_required(property_name: str) -> bool:
	return bool(cint(frappe.db.get_value("Hotel Property", property_name, "guest_register_required")))


def nationality_class(property_name: str, nationality: str | None) -> str:
	company = frappe.db.get_value("Hotel Property", property_name, "company")
	home = frappe.get_cached_value("Company", company, "country") if company else None
	return RESIDENT if nationality and home and nationality == home else FOREIGN_CLASS


def requirements(property_name: str, klass: str) -> tuple[str, ...]:
	"""The details the property needs for a guest of this class (Resident or Foreign)."""
	rows = frappe.get_all(
		"Guest Register Requirement",
		filters={"parent": property_name, "parenttype": "Hotel Property"},
		fields=["applies_to", "register_field"],
		order_by="idx asc",
	)
	if not rows:
		return DEFAULT_REQUIREMENTS[klass]
	wanted = {ALL, RESIDENTS if klass == RESIDENT else FOREIGN}
	return tuple(dict.fromkeys(row.register_field for row in rows if row.applies_to in wanted))


def _details(stay_guest: str) -> frappe._dict:
	guest = frappe.db.get_value(
		STAY_GUEST,
		stay_guest,
		[
			"name",
			"property",
			"stay_reservation",
			"guest_profile",
			"guest_name",
			"age_category",
			"arrived_from",
			"next_destination",
			"acceptance_reference",
		],
		as_dict=True,
	)
	profile = (
		frappe.db.get_value(
			PROFILE,
			guest.guest_profile,
			["full_name", "nationality", "id_document_type", "id_document_hint", "date_of_birth"],
			as_dict=True,
		)
		or frappe._dict()
	)
	from frappe.utils.password import get_decrypted_password

	guest.profile = profile
	guest.id_number = (
		get_decrypted_password(PROFILE, guest.guest_profile, "id_document_number", raise_exception=False)
		if guest.guest_profile
		else None
	)
	guest.klass = nationality_class(guest.property, profile.get("nationality"))
	return guest


def _has(guest: frappe._dict, field: str) -> bool:
	return bool(
		{
			NATIONALITY: guest.profile.get("nationality"),
			ID_DOCUMENT: guest.profile.get("id_document_type") and guest.id_number,
			DATE_OF_BIRTH: guest.profile.get("date_of_birth"),
			ARRIVED_FROM: (guest.arrived_from or "").strip(),
			NEXT_DESTINATION: (guest.next_destination or "").strip(),
			ACCEPTANCE: (guest.acceptance_reference or "").strip(),
		}[field]
	)


def missing(stay_guest: str) -> list[str]:
	"""Required details this guest hasn't given yet. Empty when the register is off or for a child."""
	guest = _details(stay_guest)
	if guest.age_category != "Adult" or not is_required(guest.property):
		return []
	return [field for field in requirements(guest.property, guest.klass) if not _has(guest, field)]


def assert_complete(stay_guests: list[str]) -> None:
	"""Refuse check-in while a registering guest is missing a required detail."""
	gaps = []
	for name in stay_guests:
		fields = missing(name)
		if fields:
			gaps.append(
				_("{0}: {1}").format(
					frappe.db.get_value(STAY_GUEST, name, "guest_name"),
					", ".join(_(field) for field in fields),
				)
			)
	if gaps:
		frappe.throw(
			_("The guest register needs: {0}. Add them to the guest's profile or registration.").format(
				"; ".join(gaps)
			),
			RegisterIncompleteError,
		)


def capture(stay_guest: str) -> str | None:
	"""Write the guest's register entry at check-in. Safe to call again; returns the entry."""
	guest = _details(stay_guest)
	if guest.age_category != "Adult" or not is_required(guest.property):
		return None
	existing = frappe.db.get_value(ENTRY, {"stay_guest": stay_guest}, "name")
	if existing:
		return existing
	stay = frappe.db.get_value(
		STAY, guest.stay_reservation, ["arrival_date", "departure_date", "room_occupancy"], as_dict=True
	)
	wanted = set(requirements(guest.property, guest.klass))
	room = frappe.db.get_value(
		"Room Assignment",
		{"stay_reservation": guest.stay_reservation, "status": ["in", ("Assigned", "Occupied")]},
		"room_number",
	)
	doc = frappe.get_doc(
		{
			"doctype": ENTRY,
			"property": guest.property,
			"stay_reservation": guest.stay_reservation,
			"stay_guest": guest.name,
			"guest_profile": guest.guest_profile,
			"full_name": guest.profile.get("full_name") or guest.guest_name,
			"nationality": guest.profile.get("nationality"),
			"nationality_class": guest.klass,
			"id_document_type": guest.profile.get("id_document_type") if ID_DOCUMENT in wanted else None,
			"id_document_hint": mask_document_number(guest.id_number) if ID_DOCUMENT in wanted else None,
			"id_document_number": guest.id_number if ID_DOCUMENT in wanted else None,
			"date_of_birth": guest.profile.get("date_of_birth") if DATE_OF_BIRTH in wanted else None,
			"arrived_from": guest.arrived_from if ARRIVED_FROM in wanted else None,
			"next_destination": guest.next_destination if NEXT_DESTINATION in wanted else None,
			"acceptance_reference": guest.acceptance_reference,
			"arrival_date": stay.arrival_date,
			"departure_date": stay.departure_date,
			"room_number": room,
			"checked_in_at": now_datetime(),
			"captured_by": frappe.session.user,
		}
	)
	doc.flags[SERVICE_FLAG] = True
	doc.insert(ignore_permissions=True)
	return doc.name


# --------------------------------------------------------------------------- reading


def _require(roles, what: str) -> None:
	if not set(roles) & set(frappe.get_roles()):
		raise frappe.PermissionError(_("You are not allowed to {0}.").format(what))


def reveal(entry: str) -> dict:
	"""The full document number on a register entry, for a role allowed to see it. Recorded."""
	_require(REVEAL_ROLES, _("see full document numbers in the guest register"))
	from frappe.utils.password import get_decrypted_password

	row = frappe.db.get_value(
		ENTRY, entry, ["name", "property", "stay_reservation", "id_document_type"], as_dict=True
	)
	if not row:
		raise frappe.DoesNotExistError(_("Guest Register Entry {0} does not exist.").format(entry))
	number = get_decrypted_password(ENTRY, entry, "id_document_number", raise_exception=False)
	log_event(
		ENTRY,
		entry,
		"Sensitive Data Viewed",
		reason=_("Guest register document number shown"),
		data={"field": "id_document_number"},
		property_name=row.property,
	)
	return {"id_document_type": row.id_document_type, "id_document_number": number}


FIELDS = [
	"name",
	"full_name",
	"nationality",
	"nationality_class",
	"id_document_type",
	"id_document_hint",
	"date_of_birth",
	"arrival_date",
	"departure_date",
	"room_number",
	"arrived_from",
	"next_destination",
	"acceptance_reference",
	"stay_reservation",
	"checked_in_at",
]


def entries(property_name: str, from_date, to_date) -> list[dict]:
	"""Register entries by arrival date, document numbers masked."""
	rows = frappe.get_all(
		ENTRY,
		filters={
			"property": property_name,
			"arrival_date": ["between", [getdate(from_date), getdate(to_date)]],
		},
		fields=FIELDS,
		order_by="arrival_date asc, checked_in_at asc",
	)
	if not set(REVEAL_ROLES) & set(frappe.get_roles()):
		for row in rows:
			row.date_of_birth = None
	return rows


def export(property_name: str, from_date, to_date) -> list[dict]:
	"""The register with full document numbers, for the authorities. Recorded with who and why."""
	_require(EXPORT_ROLES, _("export the guest register"))
	from frappe.utils.password import get_decrypted_password

	rows = entries(property_name, from_date, to_date)
	for row in rows:
		row["id_document_number"] = get_decrypted_password(
			ENTRY, row.name, "id_document_number", raise_exception=False
		)
	log_event(
		"Hotel Property",
		property_name,
		"Guest Register Exported",
		data={"from": str(getdate(from_date)), "to": str(getdate(to_date)), "entries": len(rows)},
		property_name=property_name,
	)
	return rows
