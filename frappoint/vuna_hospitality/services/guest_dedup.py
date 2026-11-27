"""Duplicate Guest Profiles: review, audited merge, and unmerge (design §19.1 and §19.2; plan F14).

**Finding them.** Two active profiles are proposed as possible duplicates when they share:

- a normalized email address, or a phone number (its last nine digits) - *Strong*;
- the exact full name and a date of birth, or the name and a nationality - *Strong*;
- only the exact full name - *Possible*: shown for confirmation, never trusted on its own.

Each pair waits in **Guest Duplicate** until someone merges it or says the two are different
people. Nothing is ever merged automatically.

**Merging** is for the roles allowed to (MERGE_ROLES), with a reason. One profile is kept; the
other is marked `merged_into` it and stays for the record. Every record that pointed at the merged
profile is re-pointed to the kept one: they are found with Frappe's own link discovery
(`get_link_fields`), so stays, folios, preferences, service records, the guest register and any
link added later all follow, as do timeline links on Communications. The kept profile takes only
the contact details it lacked, and a do-not-rent flag is never lost. Consent is not carried over,
and ERPNext Customers are not merged (ERPNext has its own Customer merge).

**Unmerging** re-points exactly the records the merge moved, still pointing at the kept profile,
and clears what the merge filled in. Every merge and unmerge is a **Guest Profile Merge** record
and an event-log entry on both profiles.
"""

import re
from itertools import combinations

import frappe
from frappe import _
from frappe.model.rename_doc import get_link_fields
from frappe.utils import cint, now_datetime

from frappoint.vuna_hospitality.constants import (
	DATA_PROTECTION_OFFICER,
	FRONT_DESK_MANAGER,
	GUEST_SERVICES_AGENT,
	HOSPITALITY_MANAGER,
	SENSITIVE_PREFERENCE_ROLES,
)
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.feature_flag import hospitality_job
from frappoint.vuna_hospitality.services.guests import phone_key

PROFILE = "Guest Profile"
DUPLICATE = "Guest Duplicate"
MERGE = "Guest Profile Merge"
SERVICE_FLAG = "from_guest_dedup"

OPEN, MERGED, NOT_DUPLICATE, SUPERSEDED = "Open", "Merged", "Not Duplicate", "Superseded"
STRONG, POSSIBLE = "Strong", "Possible"
BASES = (  # strongest first
	("Email", STRONG),
	("Phone", STRONG),
	("Name and Date of Birth", STRONG),
	("Name and Nationality", STRONG),
	("Name Only", POSSIBLE),
)

REVIEW_ROLES = (
	"System Manager",
	HOSPITALITY_MANAGER,
	FRONT_DESK_MANAGER,
	GUEST_SERVICES_AGENT,
	DATA_PROTECTION_OFFICER,
)
MERGE_ROLES = ("System Manager", HOSPITALITY_MANAGER, FRONT_DESK_MANAGER, DATA_PROTECTION_OFFICER)

# Records that keep pointing at the merged-away profile: the review and merge records, whose job
# is to name both profiles. (Profiles merged into it earlier follow it to the kept one.)
KEEP_POINTING = {(DUPLICATE, "guest_profile"), (DUPLICATE, "duplicate_profile")}
KEEP_POINTING_DOCTYPES = {MERGE}
# Details the kept profile takes when it has none.
FILL_FIELDS = (
	"salutation",
	"preferred_name",
	"email",
	"mobile_no",
	"language",
	"nationality",
	"date_of_birth",
	"vip_level",
	"customer",
	"contact",
	"user",
)
MAX_GROUP = 25  # a group bigger than this (a shared office email, say) is not proposed pairwise


class MergeError(frappe.ValidationError):
	pass


def _require(roles, what: str) -> None:
	if not set(roles) & set(frappe.get_roles()):
		raise frappe.PermissionError(_("You are not allowed to {0}.").format(what))


def can_merge(user: str | None = None) -> bool:
	return bool(set(MERGE_ROLES) & set(frappe.get_roles(user)))


# --------------------------------------------------------------------------- finding


def _name_key(value: str | None) -> str | None:
	text = re.sub(r"\s+", " ", (value or "").strip().lower())
	return text or None


def _email_key(value: str | None) -> str | None:
	text = (value or "").strip().lower()
	return text if "@" in text else None


def candidate_pairs() -> dict[tuple[str, str], str]:
	"""{(profile, profile): basis} for every pair of active profiles that look alike, strongest basis."""
	profiles = frappe.get_all(
		PROFILE,
		filters={"merged_into": ["is", "not set"]},
		fields=["name", "full_name", "email", "mobile_no", "date_of_birth", "nationality"],
	)
	groups: dict[str, dict] = {basis: {} for basis, _strength in BASES}
	for row in profiles:
		name = _name_key(row.full_name)
		keys = {
			"Email": _email_key(row.email),
			"Phone": phone_key(row.mobile_no),
			"Name and Date of Birth": f"{name}|{row.date_of_birth}" if name and row.date_of_birth else None,
			"Name and Nationality": f"{name}|{row.nationality}" if name and row.nationality else None,
			"Name Only": name,
		}
		for basis, key in keys.items():
			if key:
				groups[basis].setdefault(key, []).append(row.name)
	pairs: dict[tuple[str, str], str] = {}
	for basis, _strength in BASES:
		for members in groups[basis].values():
			if len(members) < 2 or len(members) > MAX_GROUP:
				continue
			for pair in combinations(sorted(members), 2):
				pairs.setdefault(pair, basis)
	return pairs


def pair_key(first: str, second: str) -> str:
	return ":".join(sorted((first, second)))


@hospitality_job
def propose_duplicates() -> int:
	"""Queue every new look-alike pair for review. A pair already reviewed is not proposed again."""
	strength = dict(BASES)
	known = set(frappe.get_all(DUPLICATE, pluck="pair_key"))
	created = 0
	for (first, second), basis in candidate_pairs().items():
		key = pair_key(first, second)
		if key in known:
			continue
		doc = frappe.get_doc(
			{
				"doctype": DUPLICATE,
				"guest_profile": first,
				"duplicate_profile": second,
				"basis": basis,
				"strength": strength[basis],
				"status": OPEN,
				"pair_key": key,
			}
		)
		doc.flags[SERVICE_FLAG] = True
		doc.insert(ignore_permissions=True)
		created += 1
	return created


def open_duplicates(limit: int = 100) -> list[dict]:
	"""The review queue: strong matches first."""
	rows = frappe.get_all(
		DUPLICATE,
		filters={"status": OPEN},
		fields=[
			"name",
			"guest_profile",
			"profile_name",
			"duplicate_profile",
			"duplicate_name",
			"basis",
			"strength",
		],
		order_by="creation asc",
		limit_page_length=max(1, min(cint(limit) or 100, 500)),
	)
	return sorted(rows, key=lambda row: (row.strength != STRONG, [b for b, _s in BASES].index(row.basis)))


def _summary(profile: str, sensitive: bool) -> dict:
	fields = [
		"name",
		"full_name",
		"preferred_name",
		"email",
		"mobile_no",
		"nationality",
		"language",
		"vip_level",
		"customer",
		"is_provisional",
		"creation",
		"marketing_consent",
	]
	if sensitive:
		fields.append("date_of_birth")
	row = frappe.db.get_value(PROFILE, profile, fields, as_dict=True)
	stays = frappe.get_all("Stay Guest", filters={"guest_profile": profile}, pluck="stay_reservation")
	last = frappe.get_all(
		"Stay Reservation",
		filters={"name": ["in", stays or [""]]},
		fields=["arrival_date", "property"],
		order_by="arrival_date desc",
		limit_page_length=1,
	)
	row.update(
		stays=len(set(stays)),
		last_stay=last[0].arrival_date if last else None,
		folios=frappe.db.count("Guest Folio", {"payee_guest_profile": profile}),
		services=frappe.db.count("Service Participant", {"guest_profile": profile}),
		preferences=frappe.db.count("Guest Preference", {"guest_profile": profile, "is_active": 1}),
	)
	return row


def compare(duplicate: str) -> dict:
	"""Both profiles side by side, with what matched, for the reviewer to decide."""
	_require(REVIEW_ROLES, _("review duplicate guests"))
	row = frappe.get_doc(DUPLICATE, duplicate)
	sensitive = bool(set(SENSITIVE_PREFERENCE_ROLES) & set(frappe.get_roles()))
	first, second = _summary(row.guest_profile, sensitive), _summary(row.duplicate_profile, sensitive)
	warnings = []
	if first.customer and second.customer and first.customer != second.customer:
		warnings.append(
			_(
				"They are linked to different Customers ({0} and {1}). The kept profile keeps its own; merge the Customers in ERPNext if they are the same."
			).format(first.customer, second.customer)
		)
	if row.strength == POSSIBLE:
		warnings.append(_("Only the name matches. Check the details before merging."))
	return {
		"name": row.name,
		"status": row.status,
		"basis": row.basis,
		"strength": row.strength,
		"profiles": [first, second],
		"warnings": warnings,
		"can_merge": can_merge(),
	}


# --------------------------------------------------------------------------- merging


def _lock(*profiles: str) -> None:
	table = frappe.qb.DocType(PROFILE)
	for profile in sorted(profiles):
		frappe.qb.from_(table).select(table.name).where(table.name == profile).for_update().run()


def _references(profile: str) -> list[list[str]]:
	"""[[doctype, record, field]] of every Link to the profile, found with Frappe's link discovery."""
	found = []
	for field in get_link_fields(PROFILE):
		parent, fieldname = field["parent"], field["fieldname"]
		if field.get("issingle") or (parent, fieldname) in KEEP_POINTING or parent in KEEP_POINTING_DOCTYPES:
			continue
		table = frappe.qb.DocType(parent)
		for name in (
			frappe.qb.from_(table).select(table.name).where(table[fieldname] == profile).run(pluck=True)
		):
			found.append([parent, name, fieldname])
	for name in frappe.get_all(
		"Communication Link", filters={"link_doctype": PROFILE, "link_name": profile}, pluck="name"
	):
		found.append(["Communication Link", name, "link_name"])
	return found


def merge(source: str, target: str, reason: str, duplicate: str | None = None) -> str:
	"""Merge `source` into `target` (kept). Returns the Guest Profile Merge record."""
	_require(MERGE_ROLES, _("merge guest profiles"))
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give the reason for merging these profiles."), MergeError)
	if source == target:
		frappe.throw(_("Pick two different profiles."), MergeError)
	_lock(source, target)
	rows = {
		row.name: row
		for row in frappe.get_all(
			PROFILE,
			filters={"name": ["in", [source, target]]},
			fields=[
				"name",
				"full_name",
				"merged_into",
				"restriction_flag",
				"restriction_reason",
				*FILL_FIELDS,
			],
		)
	}
	if len(rows) != 2:
		raise frappe.DoesNotExistError(_("Both Guest Profiles must exist."))
	for row in rows.values():
		if row.merged_into:
			frappe.throw(
				_("{0} was already merged into {1}.").format(row.full_name, row.merged_into), MergeError
			)
	kept, away = rows[target], rows[source]

	moved = _references(source)
	for doctype, name, fieldname in moved:
		frappe.db.set_value(doctype, name, fieldname, target, update_modified=False)

	filled = {field: away[field] for field in FILL_FIELDS if away.get(field) and not kept.get(field)}
	if away.restriction_flag and not kept.restriction_flag:
		# A do-not-rent flag on either profile must survive the merge.
		filled.update(restriction_flag=1, restriction_reason=away.restriction_reason)
	if filled:
		frappe.db.set_value(PROFILE, target, filled, update_modified=False)
	frappe.db.set_value(PROFILE, source, "merged_into", target, update_modified=False)

	basis = frappe.db.get_value(DUPLICATE, duplicate, "basis") if duplicate else None
	record = frappe.get_doc(
		{
			"doctype": MERGE,
			"status": MERGED,
			"source_profile": source,
			"source_name": away.full_name,
			"target_profile": target,
			"target_name": kept.full_name,
			"basis": basis or _("Chosen by staff"),
			"reason": reason,
			"evidence": _evidence(away, kept),
			"moved_references": frappe.as_json(moved),
			"moved_count": len(moved),
			"copied_fields": frappe.as_json(filled, indent=None) if filled else None,
			"merged_by": frappe.session.user,
			"merged_on": now_datetime(),
		}
	)
	record.flags[SERVICE_FLAG] = True
	record.insert(ignore_permissions=True)
	_close_reviews(source, target, record.name, duplicate)
	for profile, other in ((target, source), (source, target)):
		log_event(
			PROFILE,
			profile,
			"Guest Profiles Merged",
			reason=reason,
			data={
				"merge": record.name,
				"kept": target,
				"merged_away": source,
				"moved": len(moved),
				"other": other,
			},
		)
	return record.name


def _evidence(away, kept) -> str:
	same = [
		label
		for label, field in (
			(_("email"), "email"),
			(_("phone"), "mobile_no"),
			(_("nationality"), "nationality"),
			(_("date of birth"), "date_of_birth"),
		)
		if away.get(field) and away.get(field) == kept.get(field)
	]
	names = _("Names: {0} / {1}.").format(away.full_name, kept.full_name)
	return names + (" " + _("Same {0}.").format(", ".join(same)) if same else "")


def _set_review(name: str, status: str, merge_name: str | None = None, notes: str | None = None) -> None:
	doc = frappe.get_doc(DUPLICATE, name)
	doc.update(
		{
			"status": status,
			"merge": merge_name or doc.merge,
			"reviewed_by": frappe.session.user,
			"reviewed_on": now_datetime(),
			"notes": notes or doc.notes,
		}
	)
	doc.flags[SERVICE_FLAG] = True
	doc.save(ignore_permissions=True)


def _close_reviews(source: str, target: str, merge_name: str, duplicate: str | None) -> None:
	"""The reviewed pair is Merged; other open pairs naming the merged-away profile are Superseded
	(the daily proposal finds them again against the kept profile)."""
	key = pair_key(source, target)
	for row in frappe.get_all(
		DUPLICATE,
		filters={"status": OPEN},
		or_filters={"guest_profile": source, "duplicate_profile": source, "pair_key": key},
		fields=["name", "pair_key"],
	):
		if row.name == duplicate or row.pair_key == key:
			_set_review(row.name, MERGED, merge_name)
		else:
			_set_review(
				row.name, SUPERSEDED, merge_name, _("{0} was merged into {1}.").format(source, target)
			)


def not_duplicate(duplicate: str, reason: str | None = None) -> None:
	"""The two are different people: the pair is not proposed again."""
	_require(REVIEW_ROLES, _("review duplicate guests"))
	row = frappe.get_doc(DUPLICATE, duplicate)
	if row.status != OPEN:
		frappe.throw(_("This pair was already reviewed ({0}).").format(_(row.status)))
	_set_review(duplicate, NOT_DUPLICATE, notes=(reason or "").strip() or None)
	log_event(
		PROFILE,
		row.guest_profile,
		"Guest Duplicate Dismissed",
		reason=reason,
		data={"other": row.duplicate_profile},
	)


def unmerge(merge_name: str, reason: str) -> None:
	"""Undo a merge: move back exactly what it moved, and clear what it filled in."""
	_require(MERGE_ROLES, _("unmerge guest profiles"))
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give the reason for unmerging."), MergeError)
	record = frappe.get_doc(MERGE, merge_name)
	if record.status != MERGED:
		frappe.throw(_("This merge was already undone."), MergeError)
	source, target = record.source_profile, record.target_profile
	_lock(source, target)
	if frappe.db.get_value(PROFILE, target, "merged_into"):
		frappe.throw(
			_("{0} has since been merged into another profile. Undo that merge first.").format(target),
			MergeError,
		)
	moved_back = 0
	for doctype, name, fieldname in frappe.parse_json(record.moved_references or "[]"):
		if frappe.db.exists(doctype, name) and frappe.db.get_value(doctype, name, fieldname) == target:
			frappe.db.set_value(doctype, name, fieldname, source, update_modified=False)
			moved_back += 1
	filled = frappe.parse_json(record.copied_fields or "{}") or {}
	current = frappe.db.get_value(PROFILE, target, list(filled), as_dict=True) if filled else {}
	# Only what is still as the merge left it: a detail edited since stays.
	meta = frappe.get_meta(PROFILE)
	cleared = {
		field: 0 if meta.get_field(field) and meta.get_field(field).fieldtype == "Check" else None
		for field, value in filled.items()
		if str(current.get(field)) == str(value)
	}
	if cleared:
		frappe.db.set_value(PROFILE, target, cleared, update_modified=False)
	frappe.db.set_value(PROFILE, source, "merged_into", None, update_modified=False)
	record.update(
		{
			"status": "Unmerged",
			"unmerged_by": frappe.session.user,
			"unmerged_on": now_datetime(),
			"unmerge_reason": reason,
		}
	)
	record.flags[SERVICE_FLAG] = True
	record.save(ignore_permissions=True)
	review = frappe.db.get_value(DUPLICATE, {"merge": merge_name, "status": MERGED}, "name")
	if review:
		_set_review(review, NOT_DUPLICATE, notes=_("Unmerged: {0}").format(reason))
	for profile in (source, target):
		log_event(
			PROFILE,
			profile,
			"Guest Profiles Unmerged",
			reason=reason,
			data={"merge": merge_name, "moved_back": moved_back},
		)
