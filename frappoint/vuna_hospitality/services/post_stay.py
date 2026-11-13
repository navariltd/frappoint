"""Post-stay folios (design §15.9; feature F12).

When a guest checks out, every folio not yet invoiced becomes **Post-Stay Open** until the
property's "Post-Stay Window" has passed, counted from the departure business date. A late charge
(a minibar discrepancy, damage) can post there with the original guest, stay, and room. An
invoiced folio stays closed: a late charge opens a new post-stay folio for the same payee.

Late charges need a Front Desk Manager and a reason (folio.post_manual_charge checks it). Night
audit's "Close Post-Stay Folios" stage then closes each folio whose window ended: a folio with
nothing owed is settled into its invoice (or closed, if it has nothing to invoice); one that still
owes is listed for follow-up.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, now_datetime

from frappoint.vuna_hospitality.constants import FOLIO_MANAGER_ROLES
from frappoint.vuna_hospitality.services import folio
from frappoint.vuna_hospitality.services.money import to_minor
from frappoint.vuna_hospitality.services.reservations import STAY, _row
from frappoint.vuna_hospitality.services.status_commands import transition

CHECKED_OUT = "Checked Out"
DEFAULT_WINDOW_DAYS = 2


class PostStayError(frappe.ValidationError):
	pass


def window_end(stay_name: str):
	"""The last business date a late charge can post for the stay."""
	stay = _row(STAY, stay_name, ["property", "departure_date"])
	days = frappe.db.get_value("Hotel Property", stay.property, "post_stay_window_days")
	days = DEFAULT_WINDOW_DAYS if days is None else cint(days)
	return add_days(getdate(stay.departure_date), days)


def open_after_check_out(stay_name: str) -> list[str]:
	"""At check-out, keep the stay's open folios open for late charges until the window ends."""
	until = window_end(stay_name)
	opened = []
	for name in folio.stay_folios(stay_name, (folio.OPEN,)):
		transition(
			frappe.get_doc(folio.FOLIO, name),
			folio.POST_STAY_OPEN,
			updates={"post_stay_until": until},
			event_type="Folio Post-Stay Open",
			ignore_permissions=True,
		)
		opened.append(name)
	return opened


def check_late_folio(stay) -> None:
	"""A new folio after check-out is for a late charge: a manager, inside the window."""
	if not set(FOLIO_MANAGER_ROLES) & set(frappe.get_roles()):
		frappe.throw(_("Only a Front Desk Manager can open a folio after check-out."), frappe.PermissionError)
	business_date = getdate(frappe.db.get_value("Hotel Property", stay.property, "business_date"))
	until = window_end(stay.name)
	if business_date > getdate(until):
		frappe.throw(
			_("Late charges for stay {0} closed on {1}.").format(stay.name, frappe.format(until, "Date")),
			PostStayError,
		)


def mark_late_folio(folio_name: str, stay_name: str) -> None:
	transition(
		frappe.get_doc(folio.FOLIO, folio_name),
		folio.POST_STAY_OPEN,
		updates={"post_stay_until": window_end(stay_name)},
		event_type="Folio Post-Stay Open",
		ignore_permissions=True,
	)


def expired_folios(property_name: str, business_date) -> list[str]:
	"""Post-stay folios whose window ends with `business_date`."""
	return frappe.get_all(
		folio.FOLIO,
		filters={
			"property": property_name,
			"status": folio.POST_STAY_OPEN,
			"post_stay_until": ["<=", getdate(business_date)],
		},
		pluck="name",
		order_by="post_stay_until asc, name asc",
	)


def close_expired(folio_name: str) -> str:
	"""Close one folio whose window ended. Returns "closed", "settled", "pending" or "owing"."""
	from frappoint.vuna_hospitality.services import settlement

	row = folio.lock_folio(folio_name)
	if row.status != folio.POST_STAY_OPEN:
		return "skipped"
	if to_minor(row.balance, row.currency):
		return "owing"
	if not folio.has_billable_activity(folio_name):
		transition(
			frappe.get_doc(folio.FOLIO, folio_name),
			folio.CLOSED,
			reason=_("Post-stay window ended"),
			updates={"closed_at": now_datetime(), "closed_by": frappe.session.user, "pending_total": 0},
			event_type="Folio Closed",
			ignore_permissions=True,
		)
		return "closed"
	result = settlement.settle(folio_name)
	return "pending" if result["status"] == settlement.SETTLEMENT_PENDING else "settled"
