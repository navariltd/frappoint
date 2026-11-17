"""Night Audit page endpoints: see tonight's audit and start (or restart) it.

Night audit is started by a Night Auditor or a manager, never by a scheduler (plan F8). Reading the
page needs read access to Night Audit Run and the property.
"""

import frappe

from frappoint.vuna_hospitality.constants import NIGHT_AUDIT_ROLES
from frappoint.vuna_hospitality.services import night_audit
from frappoint.vuna_hospitality.services.feature_flag import require_hospitality
from frappoint.vuna_hospitality.services.property_scope import assert_property_access


def _overview(property_name: str) -> dict:
	overview = night_audit.night_audit_overview(property_name)
	overview["can_start"] = bool(set(frappe.get_roles()) & set(NIGHT_AUDIT_ROLES))
	return overview


@frappe.whitelist()
@require_hospitality
def get_night_audit(property: str) -> dict:
	"""Tonight's audit for the property: its run and stages, a preview, and recent runs."""
	assert_property_access(property)
	frappe.has_permission(night_audit.RUN, "read", throw=True)
	return _overview(property)


@frappe.whitelist(methods=["POST"])
@require_hospitality
def start_night_audit(property: str) -> dict:
	"""Close the property's business date in the background. A failed run restarts where it stopped."""
	frappe.only_for(NIGHT_AUDIT_ROLES)
	assert_property_access(property)
	run_name = night_audit.start_night_audit(property)
	overview = _overview(property)
	# The job is queued only when this request commits, so Redis doesn't know it yet. It is
	# running as far as the desk is concerned, so the page keeps following it.
	if overview.get("run") and overview["run"].get("name") == run_name:
		overview["run"]["job_active"] = True
	return overview
