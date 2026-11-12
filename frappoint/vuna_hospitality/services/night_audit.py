"""Night audit, minimal (design §21, §28.6; feature F8).

Night audit closes a property's business day. A Night Auditor starts it, never a scheduler. It runs
as a background job on the `long` queue, as one **Night Audit Run** per property and business
date, in three stages:

1. **Post room charges.** Every in-house stay's Stay Rate Night for the day is posted to the stay's
   default folio with the key `night:<stay>:<date>:room`, carrying the business date being closed.
   The job commits after each night, so a run that dies keeps what it posted.
2. **Roll statuses.** Stays arriving on the next business date become Due In, and stays leaving
   by then become Due Out. Arrivals that never checked in are listed as no-show candidates;
   no-show charges and status come with F12.
3. **Advance the business date**, as the last step and in its own transaction.

A failed run is started again from the Night Audit page: completed stages are skipped and the
unfinished stage runs again. Posting keys make the repeat safe, so no night is charged twice. A run
left "Running" by a worker that died is treated as failed when someone starts it again.

Check-out also posts the nights a guest used that night audit hasn't posted yet (`post_due_nights`),
with the same keys, so the guest settles them before leaving.
"""

from collections import Counter

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, now_datetime
from frappe.utils.background_jobs import is_job_enqueued

from frappoint.vuna_hospitality.doctype.hospitality_settings.hospitality_settings import (
	is_hospitality_enabled,
)
from frappoint.vuna_hospitality.doctype.hotel_property.hotel_property import BUSINESS_DATE_FLAG
from frappoint.vuna_hospitality.services import folio
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.inventory import InventoryConflictError
from frappoint.vuna_hospitality.services.money import from_minor, to_minor
from frappoint.vuna_hospitality.services.reservations import RATE_NIGHT, STAY, _lock_row, _lock_stay, _row
from frappoint.vuna_hospitality.services.rooms import refresh_room_sellability
from frappoint.vuna_hospitality.services.status_commands import transition

RUN = "Night Audit Run"
STAGE = "Night Audit Run Stage"
PROPERTY = "Hotel Property"

QUEUED, RUNNING, COMPLETED, FAILED = "Queued", "Running", "Completed", "Failed"
ACTIVE_STATUSES = (QUEUED, RUNNING)
PENDING = "Pending"

POST_ROOM_CHARGES = "Post Room Charges"
ROLL_STATUSES = "Roll Statuses"
ADVANCE_BUSINESS_DATE = "Advance Business Date"
STAGES = (POST_ROOM_CHARGES, ROLL_STATUSES, ADVANCE_BUSINESS_DATE)

IN_HOUSE_STATUSES = ("In House", "Due Out")
NO_SHOW_CANDIDATE_STATUSES = ("Confirmed", "Due In")

BATCH_SIZE = 100
CONFLICT_ATTEMPTS = 3
JOB_TIMEOUT = 60 * 60
LISTED_FAILURES = 10
NIGHT_SAVEPOINT = "night_audit_night"
STAGE_SAVEPOINT = "night_audit_stage"
REALTIME_EVENT = "hospitality_night_audit"

# Set on runs created by this service; the DocType refuses inserts without it.
SERVICE_FLAG = "from_night_audit"


class NightAuditError(frappe.ValidationError):
	"""Night audit can't start: the property is inactive, or its day is already closed."""


class NightAuditRunningError(NightAuditError):
	"""A run for this property and business date is already queued or running."""


def run_name(property_name: str, business_date) -> str:
	return f"NA-{property_name}-{getdate(business_date)}"


# --------------------------------------------------------------------------- room nights


def post_room_night(night_name: str, business_date=None) -> dict | None:
	"""Post one Stay Rate Night to its stay's default folio, exactly once.

	Returns {"name", "created"} like `folio.post`, or None when the night was waived (a zero rate)
	or is no longer pending. `business_date` is the day the posting belongs to; it defaults to the
	property's current business date.
	"""
	night = _row(
		RATE_NIGHT,
		night_name,
		["name", "stay_reservation", "night_date", "total", "posting_state", "posting_key"],
	)
	if not night:
		frappe.throw(_("Stay Rate Night {0} does not exist.").format(night_name), frappe.DoesNotExistError)
	if night.posting_state == "Posted":
		existing = frappe.db.get_value(folio.TRANSACTION, {"posting_key": night.posting_key}, "name")
		return {"name": existing, "created": False}
	if night.posting_state != PENDING:
		return None

	stay = _row(STAY, night.stay_reservation, ["name", "property", "rate_plan", "default_folio", "currency"])
	key = f"night:{stay.name}:{getdate(night.night_date)}:room"
	if not to_minor(night.total, stay.currency):
		# A complimentary night has nothing to charge.
		frappe.db.set_value(
			RATE_NIGHT,
			night.name,
			{"posting_state": "Waived", "override_reason": _("Zero rate")},
		)
		return None

	folio_name = stay.default_folio or folio.ensure_default_folio(stay.name)
	charge_code = frappe.db.get_value("Rate Plan", stay.rate_plan, "room_charge_code")
	primary_guest = frappe.db.get_value(
		"Stay Guest",
		{"stay_reservation": stay.name, "role": "Primary", "status": ["!=", "Removed"]},
		"name",
	)
	result = folio.post(
		folio_name,
		charge_code,
		night.total,
		posting_key=key,
		business_date=business_date,
		service_date=night.night_date,
		source_doctype=RATE_NIGHT,
		source_name=night.name,
		stay_guest=primary_guest,
	)
	frappe.db.set_value(RATE_NIGHT, night.name, {"posting_state": "Posted", "posting_key": key})
	folio.refresh_pending(folio_name)
	return result


def post_due_nights(stay_name: str, before, business_date=None) -> list[dict]:
	"""Post the stay's pending nights before `before`: the nights a departing guest has used."""
	nights = frappe.get_all(
		RATE_NIGHT,
		filters={
			"stay_reservation": stay_name,
			"posting_state": PENDING,
			"night_date": ["<", getdate(before)],
		},
		pluck="name",
		order_by="night_date asc",
	)
	posted = [post_room_night(name, business_date) for name in nights]
	return [result for result in posted if result]


# --------------------------------------------------------------------------- starting a run


def start_night_audit(property_name: str) -> str:
	"""Queue night audit for the property's current business date. Returns the run name.

	A failed run, or one whose worker died, is queued again to finish its remaining stages. A run
	that is still queued or running is refused.
	"""
	_lock_row(PROPERTY, property_name)
	prop = _row(PROPERTY, property_name, ["name", "business_date", "is_active"])
	if not prop.is_active:
		frappe.throw(_("Hotel Property {0} is inactive.").format(property_name), NightAuditError)
	business_date = getdate(prop.business_date)
	name = run_name(property_name, business_date)

	if frappe.db.exists(RUN, name):
		run = frappe.get_doc(RUN, name)
		if run.status == COMPLETED:
			frappe.throw(
				_("Night audit for {0} already closed {1}.").format(
					property_name, frappe.format(business_date, "Date")
				),
				NightAuditError,
			)
		if run.status in ACTIVE_STATUSES:
			if run.job_id and is_job_enqueued(run.job_id):
				frappe.throw(
					_("Night audit for {0} is already {1}.").format(property_name, _(run.status.lower())),
					NightAuditRunningError,
				)
			# The worker died (or the job was lost) before the run finished.
			transition(
				run,
				FAILED,
				reason=_("The background job stopped before the run finished."),
				updates={"error": _("The background job stopped before the run finished.")},
				event_type="Night Audit Failed",
				ignore_permissions=True,
			)
		for stage in run.stages:
			if stage.status != COMPLETED:
				stage.status = PENDING
		transition(
			run,
			QUEUED,
			updates={"started_by": frappe.session.user, "error": None, "finished_at": None},
			event_type="Night Audit Restarted",
			ignore_permissions=True,
		)
	else:
		run = frappe.get_doc(
			{
				"doctype": RUN,
				"property": property_name,
				"business_date": business_date,
				"status": QUEUED,
				"started_by": frappe.session.user,
				"stages": [{"stage": stage, "status": PENDING} for stage in STAGES],
			}
		)
		run.flags[SERVICE_FLAG] = True
		run.insert(ignore_permissions=True)
		log_event(RUN, run.name, "Night Audit Queued", to_status=QUEUED, property_name=property_name)

	run.db_set("job_id", f"night-audit-{run.name}", update_modified=False)
	frappe.enqueue(
		"frappoint.vuna_hospitality.services.night_audit.execute_run",
		queue="long",
		timeout=JOB_TIMEOUT,
		job_id=run.job_id,
		deduplicate=True,
		enqueue_after_commit=True,
		run_name=run.name,
	)
	return run.name


# --------------------------------------------------------------------------- running a run


def execute_run(run_name: str) -> str:
	"""The background job: run each unfinished stage in order. Returns the run's final status."""
	run = frappe.get_doc(RUN, run_name)
	if run.status != QUEUED:
		# A duplicate job, or one started after the run was handled.
		return run.status
	if not is_hospitality_enabled():
		_fail(run, None, _("Hospitality was turned off before night audit ran."))
		return FAILED

	transition(
		run,
		RUNNING,
		updates={"started_at": now_datetime(), "attempts": cint(run.attempts) + 1},
		event_type="Night Audit Started",
		ignore_permissions=True,
	)
	# The job owns its transactions and commits after each step (§28.6).
	frappe.db.commit()  # nosemgrep
	_publish(run)

	for stage in run.stages:
		if stage.status == COMPLETED:
			continue
		_update_stage(stage, status=RUNNING, started_at=now_datetime(), finished_at=None, message=None)
		frappe.db.commit()  # nosemgrep
		_publish(run, stage.stage)

		frappe.db.savepoint(STAGE_SAVEPOINT)
		try:
			counts, message = STAGE_RUNNERS[stage.stage](run, stage)
		except Exception as error:
			_rollback_to(STAGE_SAVEPOINT)
			frappe.log_error(
				title=f"Night audit {run.name}: {stage.stage}", reference_doctype=RUN, reference_name=run.name
			)
			_fail(run, stage, str(error) or error.__class__.__name__)
			return FAILED

		failed = counts.get("failed", 0)
		_update_stage(
			stage,
			status=FAILED if failed else COMPLETED,
			finished_at=now_datetime(),
			message=message,
			**counts,
		)
		if failed:
			_fail(run, stage, _("{0} could not finish: {1}").format(_(stage.stage), message))
			return FAILED
		frappe.db.commit()  # nosemgrep
		_publish(run, stage.stage)

	run.reload()
	transition(
		run,
		COMPLETED,
		updates={"finished_at": now_datetime()},
		event_type="Night Audit Completed",
		ignore_permissions=True,
	)
	frappe.db.commit()  # nosemgrep
	_publish(run)
	return COMPLETED


def _fail(run, stage, message: str) -> None:
	if stage is not None and stage.status != FAILED:
		_update_stage(stage, status=FAILED, finished_at=now_datetime(), message=message)
	run.reload()
	transition(
		run,
		FAILED,
		reason=message,
		updates={"error": message, "finished_at": now_datetime()},
		event_type="Night Audit Failed",
		ignore_permissions=True,
	)
	frappe.db.commit()  # nosemgrep
	_publish(run)


def _update_stage(stage, **values) -> None:
	stage.update(values)
	frappe.db.set_value(STAGE, stage.name, values, update_modified=False)


def _rollback_to(savepoint: str) -> None:
	"""Undo the uncommitted work since `savepoint`. If the database already rolled the whole
	transaction back (a deadlock) or a commit released the savepoint, roll back what is left."""
	try:
		frappe.db.rollback(save_point=savepoint)
	except Exception:
		frappe.db.rollback()


def _publish(run, stage: str | None = None) -> None:
	frappe.publish_realtime(
		REALTIME_EVENT,
		{"run": run.name, "property": run.property, "status": run.status, "stage": stage},
		doctype=RUN,
		docname=run.name,
	)


# --------------------------------------------------------------------------- stages


def _post_room_charges(run, stage) -> tuple[dict, str | None]:
	"""Stage 1: post tonight's room charge for every in-house stay, one committed night at a time."""
	counts: Counter = Counter()
	failures: dict[str, str] = {}
	while True:
		nights = _nights_to_post(run.property, run.business_date, exclude=list(failures), limit=BATCH_SIZE)
		if not nights:
			break
		for name in nights:
			try:
				result = _post_night_with_retry(name, run.business_date)
			except Exception as error:
				failures[name] = str(error) or error.__class__.__name__
				frappe.log_error(
					title=f"Night audit {run.name}: room charge {name}",
					reference_doctype=RATE_NIGHT,
					reference_name=name,
				)
				frappe.db.commit()  # nosemgrep
				continue
			counts["processed"] += 1
			counts["posted" if result and result["created"] else "skipped"] += 1
		_update_stage(stage, **counts)
		frappe.db.commit()  # nosemgrep
		_publish(run, stage.stage)

	counts["failed"] = len(failures)
	message = None
	if failures:
		listed = "; ".join(f"{name}: {error}" for name, error in list(failures.items())[:LISTED_FAILURES])
		message = _("{0} night(s) not posted. {1}").format(len(failures), listed)
	return dict(counts), message


def _nights_to_post(property_name: str, business_date, exclude: list[str], limit: int) -> list[str]:
	night = frappe.qb.DocType(RATE_NIGHT)
	stay = frappe.qb.DocType(STAY)
	query = (
		frappe.qb.from_(night)
		.join(stay)
		.on(stay.name == night.stay_reservation)
		.select(night.name)
		.where(night.property == property_name)
		.where(night.night_date == getdate(business_date))
		.where(night.posting_state == PENDING)
		.where(stay.status.isin(IN_HOUSE_STATUSES))
		.orderby(night.name)
		.limit(limit)
	)
	if exclude:
		query = query.where(night.name.notin(exclude))
	return query.run(pluck=True)


def _post_night_with_retry(night_name: str, business_date) -> dict | None:
	"""Post one night and commit it. A lock conflict with a front-desk posting is retried in a new
	transaction; the posting key keeps the retry from charging twice."""
	for attempt in range(1, CONFLICT_ATTEMPTS + 1):
		frappe.db.savepoint(NIGHT_SAVEPOINT)
		try:
			result = post_room_night(night_name, business_date)
		except InventoryConflictError:
			_rollback_to(NIGHT_SAVEPOINT)
			frappe.db.commit()  # nosemgrep
			if attempt == CONFLICT_ATTEMPTS:
				raise
			continue
		except Exception:
			_rollback_to(NIGHT_SAVEPOINT)
			raise
		frappe.db.commit()  # nosemgrep
		return result


def _roll_statuses(run, stage) -> tuple[dict, str | None]:
	"""Stage 2: stays arriving on the next business date are Due In, stays leaving by it Due Out."""
	next_date = add_days(getdate(run.business_date), 1)
	counts: Counter = Counter()
	moves = [
		(STAY, {"property": run.property, "status": "Confirmed", "arrival_date": next_date}, "Due In"),
		(
			STAY,
			{"property": run.property, "status": "In House", "departure_date": ["<=", next_date]},
			"Due Out",
		),
	]
	for doctype, filters, to_status in moves:
		for name in frappe.get_all(doctype, filters=filters, pluck="name", order_by="name asc"):
			stay = _lock_stay(name)
			if stay.status != filters["status"]:
				counts["skipped"] += 1
				continue
			transition(stay, to_status, event_type="Night Audit Status Roll", ignore_permissions=True)
			counts["processed"] += 1
			counts["posted"] += 1
			frappe.db.commit()  # nosemgrep

	candidates = frappe.get_all(
		STAY,
		filters={
			"property": run.property,
			"status": ["in", list(NO_SHOW_CANDIDATE_STATUSES)],
			"arrival_date": ["<=", getdate(run.business_date)],
		},
		fields=["name", "lead_guest_name"],
		order_by="name asc",
	)
	message = None
	if candidates:
		listed = ", ".join(f"{row.name} ({row.lead_guest_name})" for row in candidates[:LISTED_FAILURES])
		message = _("No-show candidates, not checked in: {0}. No-show handling comes with F12.").format(
			listed
		)
	return dict(counts), message


def _advance_business_date(run, stage) -> tuple[dict, str | None]:
	"""Stage 3: move the property to the next business date. Running it again changes nothing."""
	_lock_row(PROPERTY, run.property)
	prop = frappe.get_doc(PROPERTY, run.property)
	closing = getdate(run.business_date)
	if getdate(prop.business_date) != closing:
		return {"skipped": 1}, _("The business date was already {0}.").format(
			frappe.format(prop.business_date, "Date")
		)

	next_date = add_days(closing, 1)
	prop.business_date = next_date
	prop.flags[BUSINESS_DATE_FLAG] = True
	prop.save(ignore_permissions=True)
	log_event(
		PROPERTY,
		prop.name,
		"Business Date Advanced",
		data={"from": str(closing), "to": str(next_date), "run": run.name},
		property_name=prop.name,
		business_date=closing,
	)
	# Out-of-order and out-of-service periods start and end with the business date.
	for room in frappe.get_all("Hotel Room", filters={"property": prop.name}, pluck="name"):
		refresh_room_sellability(room, next_date)
	return {"processed": 1, "posted": 1}, _("Business date is now {0}.").format(
		frappe.format(next_date, "Date")
	)


STAGE_RUNNERS = {
	POST_ROOM_CHARGES: _post_room_charges,
	ROLL_STATUSES: _roll_statuses,
	ADVANCE_BUSINESS_DATE: _advance_business_date,
}


# --------------------------------------------------------------------------- views


def night_audit_overview(property_name: str) -> dict:
	"""The Night Audit page: today's run with its stages, what tonight will do, and recent runs."""
	business_date = getdate(frappe.db.get_value(PROPERTY, property_name, "business_date"))
	name = run_name(property_name, business_date)
	current = None
	if frappe.db.exists(RUN, name):
		run = frappe.get_doc(RUN, name)
		current = run.as_dict(no_default_fields=True)
		current["name"] = run.name
		current["stages"] = [
			{
				field: stage.get(field)
				for field in (
					"stage",
					"status",
					"processed",
					"posted",
					"skipped",
					"failed",
					"started_at",
					"finished_at",
					"message",
				)
			}
			for stage in run.stages
		]
		current["job_active"] = bool(
			run.status in ACTIVE_STATUSES and run.job_id and is_job_enqueued(run.job_id)
		)

	night = frappe.qb.DocType(RATE_NIGHT)
	stay = frappe.qb.DocType(STAY)
	tonight = (
		frappe.qb.from_(night)
		.join(stay)
		.on(stay.name == night.stay_reservation)
		.select(night.total)
		.where(night.property == property_name)
		.where(night.night_date == business_date)
		.where(night.posting_state == PENDING)
		.where(stay.status.isin(IN_HOUSE_STATUSES))
	).run(pluck=True)
	currency = frappe.db.get_value(PROPERTY, property_name, "currency")
	return {
		"property": property_name,
		"business_date": business_date,
		"currency": currency,
		"run": current,
		"preview": {
			"room_nights": len(tonight),
			"room_charges": from_minor(sum(to_minor(total, currency) for total in tonight), currency),
			"arrivals_not_checked_in": frappe.db.count(
				STAY,
				{
					"property": property_name,
					"status": ["in", list(NO_SHOW_CANDIDATE_STATUSES)],
					"arrival_date": ["<=", business_date],
				},
			),
			"departures_not_checked_out": frappe.db.count(
				STAY,
				{
					"property": property_name,
					"status": ["in", list(IN_HOUSE_STATUSES)],
					"departure_date": ["<=", business_date],
				},
			),
		},
		"recent_runs": frappe.get_all(
			RUN,
			filters={"property": property_name},
			fields=["name", "business_date", "status", "started_by", "started_at", "finished_at", "attempts"],
			order_by="business_date desc",
			limit=7,
		),
	}
