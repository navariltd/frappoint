"""Status command framework.

Hotel status fields are read-only. A status changes only through `transition()`, which:

1. checks the move is in the DocType's transition table,
2. asks for a reason when the move requires one,
3. saves the document (running its normal validation),
4. writes a Hospitality Event Log entry.

Each DocType registers its table once, at import time of its controller:

    register_transitions(
        "Stay Reservation",
        {"Held": {"Confirmed", "Expired", "Cancelled"}, "Confirmed": {"Due In", "Cancelled"}},
        reason_required={("Confirmed", "Cancelled")},
    )

and calls `guard_status_change(self)` from its `validate`, so a status edited any other way
(desk form, `doc.save()`, API) is refused.
"""

from dataclasses import dataclass, field
from typing import Any

import frappe
from frappe import _

from frappoint.vuna_hospitality.services.event_log import log_event

TRANSITION_FLAG = "hospitality_status_transition"


class InvalidTransitionError(frappe.ValidationError):
	pass


@dataclass(frozen=True)
class TransitionTable:
	transitions: dict[str, frozenset[str]]
	status_field: str = "status"
	initial_statuses: frozenset[str] = field(default_factory=frozenset)
	reason_required: frozenset[tuple[str, str]] = field(default_factory=frozenset)

	def allows(self, from_status: str | None, to_status: str) -> bool:
		return to_status in self.transitions.get(from_status or "", frozenset())

	def needs_reason(self, from_status: str | None, to_status: str) -> bool:
		return (from_status, to_status) in self.reason_required or ("*", to_status) in self.reason_required


_REGISTRY: dict[str, TransitionTable] = {}


def register_transitions(
	doctype: str,
	transitions: dict[str, set[str] | frozenset[str]],
	*,
	status_field: str = "status",
	initial_statuses: set[str] | None = None,
	reason_required: set[tuple[str, str]] | None = None,
) -> TransitionTable:
	"""Register the allowed status moves for `doctype`.

	`initial_statuses` are the statuses a new document may be created with (default: the keys
	of `transitions` that no other status leads to). `reason_required` holds (from, to) pairs;
	use "*" as `from` to require a reason for every move into `to`.
	"""
	table_transitions = {source: frozenset(targets) for source, targets in transitions.items()}
	if initial_statuses is None:
		reachable = set().union(*table_transitions.values()) if table_transitions else set()
		initial_statuses = {source for source in table_transitions if source not in reachable}

	table = TransitionTable(
		transitions=table_transitions,
		status_field=status_field,
		initial_statuses=frozenset(initial_statuses),
		reason_required=frozenset(reason_required or ()),
	)
	_REGISTRY[doctype] = table
	return table


def get_transition_table(doctype: str) -> TransitionTable:
	try:
		return _REGISTRY[doctype]
	except KeyError:
		raise InvalidTransitionError(_("{0} has no status transitions registered.").format(doctype)) from None


def allowed_transitions(doc) -> list[str]:
	"""The statuses `doc` may move to next, for building UI actions."""
	table = get_transition_table(doc.doctype)
	return sorted(table.transitions.get(doc.get(table.status_field) or "", ()))


def transition(
	doc,
	to_status: str,
	*,
	reason: str | None = None,
	updates: dict[str, Any] | None = None,
	data: dict[str, Any] | None = None,
	event_type: str = "Status Changed",
	ignore_permissions: bool = False,
) -> dict[str, Any]:
	"""Move `doc` to `to_status`, applying `updates` in the same save, and audit it.

	`doc` may be a Document or a (doctype, name) tuple. Moving to the current status is a no-op.
	"""
	if isinstance(doc, tuple):
		doc = frappe.get_doc(*doc)

	table = get_transition_table(doc.doctype)
	from_status = doc.get(table.status_field)

	if from_status == to_status:
		return {"name": doc.name, "from": from_status, "to": to_status, "changed": False}

	if not table.allows(from_status, to_status):
		raise InvalidTransitionError(
			_("{0} {1} cannot move from {2} to {3}.").format(
				_(doc.doctype), doc.name, _(from_status or "-"), _(to_status)
			)
		)

	reason = (reason or "").strip() or None
	if table.needs_reason(from_status, to_status) and not reason:
		raise InvalidTransitionError(
			_("A reason is required to move {0} {1} to {2}.").format(_(doc.doctype), doc.name, _(to_status))
		)

	if updates:
		doc.update(updates)
	doc.set(table.status_field, to_status)

	doc.flags[TRANSITION_FLAG] = True
	try:
		doc.save(ignore_permissions=ignore_permissions)
	finally:
		doc.flags[TRANSITION_FLAG] = False

	log_event(
		doc.doctype,
		doc.name,
		event_type,
		from_status=from_status,
		to_status=to_status,
		reason=reason,
		data=data,
	)
	return {"name": doc.name, "from": from_status, "to": to_status, "changed": True}


def guard_status_change(doc) -> None:
	"""Call from a registered DocType's `validate`. Refuses status edits made outside `transition()`."""
	table = get_transition_table(doc.doctype)
	status = doc.get(table.status_field)

	if doc.is_new():
		if table.initial_statuses and status not in table.initial_statuses:
			raise InvalidTransitionError(
				_("A new {0} must start in one of: {1}.").format(
					_(doc.doctype), ", ".join(sorted(table.initial_statuses))
				)
			)
		return

	if doc.flags.get(TRANSITION_FLAG):
		return

	if doc.has_value_changed(table.status_field):
		raise InvalidTransitionError(
			_("The status of {0} {1} can only be changed through its actions, not edited directly.").format(
				_(doc.doctype), doc.name
			)
		)
