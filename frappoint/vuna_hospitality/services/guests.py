"""Guest profiles (design §19.1, §30.15; feature F4).

A Guest Profile is the durable identity of a person who books, stays, uses a service, or pays. It
is not the ERPNext Customer: a company Customer pays for many guests, and a booker may never stay.
Profiles are shared by every property, so a returning guest is recognized at any of them.

This module holds the rules that other features call: contact normalization, search, quick
creation from the booking screen, linking a Customer, relationships, and the provisional-guest
check that registration (F6) runs. Deterministic matching, duplicate review and merging come in F14.
"""

import re

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.utils import cint, getdate, today, validate_email_address

from frappoint.vuna_hospitality.services.event_log import log_event

GUEST_PROFILE = "Guest Profile"
GUEST_RELATIONSHIP = "Guest Relationship"

# Phone numbers are compared on their last digits, so "0712 345 678" and "+254 712 345 678" match.
PHONE_MATCH_DIGITS = 9
MIN_PHONE_DIGITS = 6
MAX_PHONE_DIGITS = 15
DEFAULT_SEARCH_LIMIT = 20

MATCH_EMAIL = "Email"
MATCH_PHONE = "Phone"
MATCH_NAME = "Name"

# "<related guest> is the <type> of <guest>"; the reverse row reads with the inverse type.
INVERSE_RELATIONSHIP = {
	"Spouse/Partner": "Spouse/Partner",
	"Parent": "Child",
	"Child": "Parent",
	"Guardian": "Ward",
	"Ward": "Guardian",
	"Sibling": "Sibling",
	"Colleague": "Colleague",
	"Assistant": "Principal",
	"Principal": "Assistant",
	"Other": "Other",
}

SEARCH_FIELDS = [
	"name",
	"full_name",
	"preferred_name",
	"email",
	"mobile_no",
	"vip_level",
	"restriction_flag",
	"is_provisional",
	"customer",
]


class ProvisionalGuestError(frappe.ValidationError):
	"""The guest is still provisional (unnamed) and must be completed first."""


def normalize_email(value: str | None) -> str | None:
	"""Trim and lower-case an email address, and reject one that isn't valid."""
	value = (value or "").strip().lower()
	if not value:
		return None
	validate_email_address(value, throw=True)
	return value


def normalize_phone(value: str | None) -> str | None:
	"""Keep only digits, with a leading "+" for international numbers ("00" counts as "+")."""
	raw = (value or "").strip()
	if not raw:
		return None
	digits = re.sub(r"\D", "", raw)
	international = raw.startswith("+") or raw.startswith("00")
	if raw.startswith("00"):
		digits = digits[2:]
	if not MIN_PHONE_DIGITS <= len(digits) <= MAX_PHONE_DIGITS:
		frappe.throw(_("{0} is not a valid phone number.").format(frappe.bold(raw)))
	return f"+{digits}" if international else digits


def phone_key(value: str | None) -> str | None:
	"""The digits two numbers must share to count as the same phone."""
	digits = re.sub(r"\D", "", value or "")
	return digits[-PHONE_MATCH_DIGITS:] if len(digits) >= MIN_PHONE_DIGITS else None


def full_name(first_name: str | None, last_name: str | None) -> str:
	return " ".join(part.strip() for part in (first_name, last_name) if part and part.strip())


def mask_document_number(number: str | None) -> str | None:
	"""A safe hint for an ID number: only its last four characters, e.g. "•••• 5678"."""
	number = (number or "").strip()
	if not number:
		return None
	return "••••" if len(number) <= 4 else f"•••• {number[-4:]}"


# Search


def search_guests(text: str, limit: int = DEFAULT_SEARCH_LIMIT) -> list[dict]:
	"""Find guests by email, phone, or name. Each result says what it matched on.

	Text with an "@" is an email; text that is mostly digits is a phone number; anything else is a
	name, where every word must appear in the guest's name (or the one word in the preferred name).
	Merged profiles are left out. Results respect the user's permissions.
	"""
	text = (text or "").strip()
	limit = max(1, min(cint(limit) or DEFAULT_SEARCH_LIMIT, 100))
	if not text:
		return []

	if "@" in text:
		return _search(MATCH_EMAIL, [["email", "=", text.lower()]], limit)

	digits = re.sub(r"\D", "", text)
	if len(digits) >= MIN_PHONE_DIGITS and len(digits) >= len(re.sub(r"[\s+()\-.]", "", text)):
		return _search(MATCH_PHONE, [["mobile_no", "like", f"%{phone_key(digits)}"]], limit)

	words = text.split()
	filters = [["full_name", "like", f"%{word}%"] for word in words]
	or_filters = None
	if len(words) == 1:
		filters, or_filters = (
			[],
			[["full_name", "like", f"%{text}%"], ["preferred_name", "like", f"%{text}%"]],
		)
	return _search(MATCH_NAME, filters, limit, or_filters)


def _search(match: str, filters: list, limit: int, or_filters: list | None = None) -> list[dict]:
	rows = frappe.get_list(
		GUEST_PROFILE,
		filters=[*filters, ["merged_into", "is", "not set"]],
		or_filters=or_filters,
		fields=SEARCH_FIELDS,
		order_by="full_name asc",
		limit_page_length=limit,
	)
	for row in rows:
		row["match"] = match
	return rows


def find_contact_matches(email: str | None = None, mobile_no: str | None = None) -> list[dict]:
	"""Profiles that share this email or phone: shown before creating a guest, never merged."""
	results, seen = [], set()
	email, key = normalize_email(email), phone_key(normalize_phone(mobile_no))
	if email:
		results += _search(MATCH_EMAIL, [["email", "=", email]], DEFAULT_SEARCH_LIMIT)
	if key:
		results += _search(MATCH_PHONE, [["mobile_no", "like", f"%{key}"]], DEFAULT_SEARCH_LIMIT)
	return [row for row in results if not (row["name"] in seen or seen.add(row["name"]))]


# Creating and completing guests


def create_guest(
	first_name: str,
	last_name: str | None = None,
	email: str | None = None,
	mobile_no: str | None = None,
	is_provisional: bool = False,
	force: bool = False,
) -> dict:
	"""Create a guest from the booking screen.

	Unless `force` is set, a guest who shares the email or phone with an existing profile is not
	created; the matches are returned instead so staff can pick one or confirm a new profile.
	"""
	if not force:
		matches = find_contact_matches(email, mobile_no)
		if matches:
			return {"created": False, "guest": None, "matches": matches}

	guest = frappe.get_doc(
		{
			"doctype": GUEST_PROFILE,
			"first_name": first_name,
			"last_name": last_name,
			"email": email,
			"mobile_no": mobile_no,
			"is_provisional": cint(is_provisional),
		}
	).insert()
	return {"created": True, "guest": guest.name, "full_name": guest.full_name, "matches": []}


def assert_registrable(guest_profile: str) -> None:
	"""Registration (check-in) needs a real person: a provisional or merged profile is refused."""
	row = frappe.db.get_value(
		GUEST_PROFILE, guest_profile, ["full_name", "is_provisional", "merged_into"], as_dict=True
	)
	if not row:
		frappe.throw(_("Guest Profile {0} does not exist.").format(guest_profile))
	if row.merged_into:
		frappe.throw(
			_("Guest Profile {0} was merged into {1}. Use that profile instead.").format(
				guest_profile, row.merged_into
			)
		)
	if row.is_provisional:
		frappe.throw(
			_("{0} is a provisional guest. Complete their details before registration.").format(
				frappe.bold(row.full_name)
			),
			ProvisionalGuestError,
		)


# Customer link


def link_customer(guest_profile: str, customer: str | None = None, ignore_permissions: bool = False) -> str:
	"""Link the Customer that pays for this guest, creating an individual Customer if none is given.

	Many guests may share a Customer (for example, employees of one company), so an existing
	Customer is never taken over or renamed. `ignore_permissions` is for the system creating the
	payer on the guest's behalf (decision D-3), for example when a cashier takes the first payment.
	"""
	guest = frappe.get_doc(GUEST_PROFILE, guest_profile)
	if not ignore_permissions:
		guest.check_permission("write")
	if guest.is_provisional:
		frappe.throw(_("Complete the guest's details before creating a Customer for them."))

	if customer:
		if not frappe.db.exists("Customer", customer):
			frappe.throw(_("Customer {0} does not exist.").format(customer))
		linked: str = customer
	else:
		linked = str(
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": guest.full_name,
					"customer_type": "Individual",
					"customer_group": _default("customer_group", "Customer Group"),
					"territory": _default("territory", "Territory"),
					"email_id": guest.email,
					"mobile_no": guest.mobile_no,
				}
			)
			.insert(ignore_permissions=ignore_permissions)
			.name
		)

	guest.customer = linked
	guest.save(ignore_permissions=ignore_permissions)
	return linked


def _default(fieldname: str, doctype: str) -> str | None:
	value = frappe.db.get_single_value("Selling Settings", fieldname)
	if value:
		return value
	return frappe.db.get_value(doctype, {"is_group": 0}, "name") or frappe.db.get_value(doctype, {}, "name")


# Sensitive data


def reveal_id_document(guest_profile: str) -> dict:
	"""Return the guest's full ID number for a user allowed to see it, and record that they did."""
	guest = frappe.get_doc(GUEST_PROFILE, guest_profile)
	guest.check_permission("read")
	if not guest.has_permlevel_access_to("id_document_number", permission_type="read"):
		raise frappe.PermissionError(_("You are not allowed to see guest ID details."))

	number = (
		guest.get_password("id_document_number", raise_exception=False) if guest.id_document_number else None
	)
	log_event(
		GUEST_PROFILE,
		guest.name,
		"Sensitive Data Viewed",
		reason=_("ID document number shown"),
		data={"field": "id_document_number"},
	)
	return {"id_document_type": guest.id_document_type, "id_document_number": number}


# Relationships


def get_relationships(guest_profile: str, on_date=None, include_ended: bool = False) -> list[dict]:
	"""Everyone related to this guest, read from either side of each Guest Relationship.

	Each row gives the other guest and what they are to this one (e.g. "Child"). Relationships
	that ended before `on_date` (default today) are left out unless `include_ended` is set.
	"""
	on_date = getdate(on_date or today())
	table = frappe.qb.DocType(GUEST_RELATIONSHIP)
	rows = (
		frappe.qb.from_(table)
		.select(
			table.name,
			table.guest_profile,
			table.related_guest,
			table.relationship_type,
			table.valid_from,
			table.valid_to,
			table.notes,
		)
		.where((table.guest_profile == guest_profile) | (table.related_guest == guest_profile))
		.orderby(table.creation, order=Order.asc)
		.run(as_dict=True)
	)

	others = {row.related_guest if row.guest_profile == guest_profile else row.guest_profile for row in rows}
	names = (
		dict(
			frappe.get_all(
				GUEST_PROFILE,
				filters={"name": ["in", list(others)]},
				fields=["name", "full_name"],
				as_list=True,
			)
		)
		if others
		else {}
	)

	results = []
	for row in rows:
		active = (not row.valid_from or getdate(row.valid_from) <= on_date) and (
			not row.valid_to or getdate(row.valid_to) >= on_date
		)
		if not active and not include_ended:
			continue
		forward = row.guest_profile == guest_profile
		other = row.related_guest if forward else row.guest_profile
		results.append(
			{
				"relationship": row.name,
				"guest": other,
				"full_name": names.get(other),
				"relationship_type": row.relationship_type
				if forward
				else INVERSE_RELATIONSHIP[row.relationship_type],
				"valid_from": row.valid_from,
				"valid_to": row.valid_to,
				"notes": row.notes,
				"is_active": active,
			}
		)
	return results
