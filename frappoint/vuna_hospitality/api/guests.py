"""Guest profile endpoints for the booking screen and the desk form."""

import frappe
from frappe import _

from frappoint.vuna_hospitality.services import guest_dedup
from frappoint.vuna_hospitality.services import guests as guest_service
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality

GUEST_PROFILE = guest_service.GUEST_PROFILE


def _check(permission: str, guest_profile: str | None = None) -> None:
	"""Raise PermissionError unless the user has `permission` on guest profiles (or this one)."""
	frappe.has_permission(GUEST_PROFILE, permission, doc=guest_profile, throw=True)


@frappe.whitelist()
@require_hospitality
def search_guests(text: str, limit: int = guest_service.DEFAULT_SEARCH_LIMIT) -> list[dict]:
	"""Find guests by name, phone, or email."""
	_check("read")
	return guest_service.search_guests(text, limit)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def create_guest(
	first_name: str,
	last_name: str | None = None,
	email: str | None = None,
	mobile_no: str | None = None,
	is_provisional: bool = False,
	force: bool = False,
) -> dict:
	"""Create a guest, or return existing guests with the same email or phone (unless `force`)."""
	_check("create")
	return guest_service.create_guest(
		first_name,
		last_name,
		email,
		mobile_no,
		is_provisional=frappe.utils.sbool(is_provisional),
		force=frappe.utils.sbool(force),
	)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def link_customer(guest_profile: str, customer: str | None = None) -> str:
	"""Link a paying Customer to the guest, creating an individual Customer if none is given."""
	if not customer and not frappe.has_permission("Customer", "create"):
		raise frappe.PermissionError(_("You are not allowed to create Customers."))
	return guest_service.link_customer(guest_profile, customer)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def reveal_id_document(guest_profile: str) -> dict:
	"""Show the guest's full ID number. Each call is recorded in the event log."""
	return guest_service.reveal_id_document(guest_profile)


@frappe.whitelist()
@require_hospitality
def get_relationships(guest_profile: str, include_ended: bool = False) -> list[dict]:
	"""Everyone related to the guest, from either side of each relationship."""
	_check("read", guest_profile)
	return guest_service.get_relationships(guest_profile, include_ended=frappe.utils.sbool(include_ended))


# --------------------------------------------------------------------------- duplicates (F14)


def _queue() -> dict:
	return {
		"duplicates": guest_dedup.open_duplicates(),
		"recent_merges": frappe.get_all(
			guest_dedup.MERGE,
			filters={"status": "Merged"},
			fields=[
				"name",
				"source_name",
				"target_name",
				"target_profile",
				"merged_by",
				"merged_on",
				"moved_count",
			],
			order_by="merged_on desc",
			limit=10,
		),
		"can_merge": guest_dedup.can_merge(),
	}


@frappe.whitelist()
@require_hospitality
def get_duplicate_guests() -> dict:
	"""Profiles that may be the same person, and the latest merges."""
	if not set(guest_dedup.REVIEW_ROLES) & set(frappe.get_roles()):
		raise frappe.PermissionError(_("You are not allowed to review duplicate guests."))
	return _queue()


@frappe.whitelist(methods=["POST"])
@require_hospitality
def find_duplicate_guests() -> dict:
	"""Look for new look-alike profiles now (a daily job does it too)."""
	if not set(guest_dedup.REVIEW_ROLES) & set(frappe.get_roles()):
		raise frappe.PermissionError(_("You are not allowed to review duplicate guests."))
	created = guest_dedup.propose_duplicates() or 0
	return {**_queue(), "created": created}


@frappe.whitelist()
@require_hospitality
def compare_duplicate_guests(duplicate: str) -> dict:
	"""Both profiles side by side, with what matched."""
	return guest_dedup.compare(duplicate)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def merge_guests(duplicate: str, keep: str, reason: str) -> dict:
	"""Merge the pair, keeping `keep`. Audited, and can be undone."""
	row = frappe.db.get_value(
		guest_dedup.DUPLICATE, duplicate, ["guest_profile", "duplicate_profile", "status"], as_dict=True
	)
	if not row:
		raise frappe.DoesNotExistError(_("Guest Duplicate {0} does not exist.").format(duplicate))
	if row.status != guest_dedup.OPEN:
		frappe.throw(_("This pair was already reviewed ({0}).").format(_(row.status)))
	if keep not in (row.guest_profile, row.duplicate_profile):
		frappe.throw(_("Keep one of the two profiles in the pair."))
	source = row.duplicate_profile if keep == row.guest_profile else row.guest_profile
	merge_name = guest_dedup.merge(source, keep, reason, duplicate)
	return {**_queue(), "merge": merge_name}


@frappe.whitelist(methods=["POST"])
@require_hospitality
def mark_not_duplicate(duplicate: str, reason: str | None = None) -> dict:
	guest_dedup.not_duplicate(duplicate, reason)
	return _queue()


@frappe.whitelist(methods=["POST"])
@require_hospitality
def unmerge_guests(merge: str, reason: str) -> dict:
	"""Undo a merge: exactly what it moved goes back."""
	guest_dedup.unmerge(merge, reason)
	return _queue()
