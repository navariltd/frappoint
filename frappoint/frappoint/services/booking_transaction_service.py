from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, get_time, getdate, now_datetime

from frappoint.frappoint.services.availability_projector import (
	lock_counter_resource_rows,
	rebuild_counter_for_date,
)

ACTIVE_RESERVATION_STATUSES = ("Draft", "Held", "Confirmed")
RELEASE_ALLOCATION_STATUSES = ("Released", "Cancelled")


class CapacityReservationError(frappe.ValidationError):
	pass


def reserve_and_create_allocations(
	appointment_name: str,
	allocations: list[dict[str, Any]],
	booking_name: str | None = None,
	allocation_status: str = "Held",
	extra_metadata: dict[str, Any] | None = None,
	commit: bool = False,
) -> list[str]:
	"""Atomically reserve counter capacity and create allocation ledger rows.

	Each allocation payload expects:
	- resource_type
	- resource_reference
	- allocation_date
	- start_time
	- end_time
	- appointment_start_time
	- appointment_end_time
	Optional:
	- capacity_consumed (default 1)
	- buffer_before_minutes (default 0)
	- buffer_after_minutes (default 0)
	"""
	if not allocations:
		return []

	if not frappe.db.exists("Service Appointment", appointment_name):
		raise CapacityReservationError(_("Service Appointment {0} not found").format(appointment_name))
	if frappe.db.get_value("Service Appointment", appointment_name, "couple_appointment_id"):
		raise CapacityReservationError(
			_("Couple appointments must reserve capacity through the atomic pair operation")
		)

	result = _reserve_appointment_allocation_groups(
		[
			{
				"appointment_name": appointment_name,
				"booking_name": booking_name,
				"allocations": allocations,
				"allocation_status": allocation_status,
				"extra_metadata": extra_metadata or {},
			}
		],
		savepoint_prefix="reserve",
		commit=commit,
	)
	return result[appointment_name]


def reserve_couple_appointment_allocations(
	appointments: list[dict[str, Any]],
	commit: bool = False,
) -> dict[str, list[str]]:
	"""Reserve both halves of a couple booking in one database transaction.

	``appointments`` must contain exactly two dictionaries. Each dictionary accepts
	the same reservation inputs as :func:`reserve_and_create_allocations` using the
	keys ``appointment_name``, ``allocations``, ``booking_name``,
	``allocation_status`` and ``extra_metadata``. ``booking_name`` defaults to the
	appointment's booking ID, while ``allocation_status`` defaults to ``Held``.

	Both appointments and all of their counter rows are validated/reserved before
	any allocation ledger row or appointment allocation status is written. The
	returned mapping is keyed by appointment name.
	"""
	return _reserve_appointment_allocation_groups(
		appointments,
		savepoint_prefix="reserve_couple",
		commit=commit,
		couple_booking=True,
	)


def release_capacity_for_allocations(
	allocation_names: list[str] | None = None,
	appointment_name: str | None = None,
	target_status: str = "Released",
	commit: bool = False,
) -> int:
	"""Release the explicitly selected allocations or one appointment's allocations.

	This function deliberately remains appointment-scoped for couple bookings so a
	cancellation flow can honour a user's choice to keep the other appointment. Use
	:func:`release_couple_appointment_allocations` when both must be released.
	"""
	if not allocation_names and not appointment_name:
		return 0

	return _release_capacity_for_allocation_scope(
		allocation_names=allocation_names,
		appointment_names=[appointment_name] if appointment_name else None,
		target_status=target_status,
		commit=commit,
		savepoint_prefix="release",
	)


def release_couple_appointment_allocations(
	appointment_names: list[str],
	target_status: str = "Released",
	commit: bool = False,
) -> int:
	"""Atomically release all active allocations belonging to a linked pair."""
	names = _validate_couple_appointment_names(appointment_names)
	return _release_capacity_for_allocation_scope(
		appointment_names=names,
		target_status=target_status,
		commit=commit,
		savepoint_prefix="release_couple",
	)


def _release_capacity_for_allocation_scope(
	allocation_names: list[str] | None = None,
	appointment_names: list[str] | None = None,
	target_status: str = "Released",
	commit: bool = False,
	savepoint_prefix: str = "release",
) -> int:
	if target_status not in RELEASE_ALLOCATION_STATUSES:
		raise CapacityReservationError(_("Unsupported released allocation status: {0}").format(target_status))
	filters: dict[str, Any] = {"allocation_status": ["in", list(ACTIVE_RESERVATION_STATUSES)]}
	if allocation_names:
		filters["name"] = ["in", allocation_names]
	if appointment_names:
		filters["service_appointment"] = (
			appointment_names[0] if len(appointment_names) == 1 else ["in", appointment_names]
		)

	savepoint = _savepoint_name(savepoint_prefix)
	frappe.db.savepoint(savepoint)

	try:
		if appointment_names:
			# Reservation also locks appointment rows first. Taking the same scope lock
			# before discovering allocations prevents a concurrently-created ledger row
			# from falling outside a stale candidate-name snapshot.
			_lock_service_appointment_rows(appointment_names)
			if len(appointment_names) == 2:
				_validate_couple_appointment_names(appointment_names)
		candidate_rows = frappe.get_all(
			"Service Resource Allocation",
			filters=filters,
			fields=["name", "service_appointment"],
		)
		if not candidate_rows:
			return 0

		if not appointment_names:
			locked_appointment_names = sorted(
				{row.get("service_appointment") for row in candidate_rows if row.get("service_appointment")}
			)
			_lock_service_appointment_rows(locked_appointment_names)
		candidate_names = sorted({row.get("name") for row in candidate_rows if row.get("name")})
		_lock_allocation_rows(candidate_names)

		# Re-read under lock so a concurrent release cannot return the same capacity twice.
		locked_filters = {**filters, "name": ["in", candidate_names]}
		rows = frappe.get_all(
			"Service Resource Allocation",
			filters=locked_filters,
			fields=[
				"name",
				"allocation_date",
				"resource_type",
				"resource_reference",
				"start_time",
				"end_time",
				"capacity_consumed",
			],
		)
		if not rows:
			return 0

		prepared = [_prepare_release_payload(row) for row in rows]
		_apply_counter_deltas(prepared, direction="release")

		for row in rows:
			frappe.db.set_value(
				"Service Resource Allocation",
				row["name"],
				{
					"allocation_status": target_status,
					"is_confirmed": 0,
					"confirmed_at": None,
				},
				update_modified=False,
			)

		for appointment_name in appointment_names or []:
			_update_appointment_allocation_status(appointment_name, target_status)

		if commit:
			frappe.db.commit()
		return len(rows)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def confirm_held_allocations(appointment_name: str, commit: bool = False) -> int:
	"""Move held allocations to confirmed and sync appointment status field."""
	if frappe.db.get_value("Service Appointment", appointment_name, "couple_appointment_id"):
		raise CapacityReservationError(
			_("Couple appointments must confirm capacity through the atomic pair operation")
		)
	return _confirm_held_allocations_for_appointments(
		[appointment_name], commit=commit, savepoint_prefix="confirm"
	)


def confirm_couple_held_allocations(
	appointment_names: list[str],
	commit: bool = False,
) -> int:
	"""Atomically confirm all held allocation rows belonging to a linked pair."""
	names = _validate_couple_appointment_names(appointment_names)
	return _confirm_held_allocations_for_appointments(names, commit=commit, savepoint_prefix="confirm_couple")


def _confirm_held_allocations_for_appointments(
	appointment_names: list[str],
	commit: bool = False,
	savepoint_prefix: str = "confirm",
) -> int:
	savepoint = _savepoint_name(savepoint_prefix)
	frappe.db.savepoint(savepoint)
	try:
		_lock_service_appointment_rows(appointment_names)
		if len(appointment_names) == 2:
			_validate_couple_appointment_names(appointment_names)
		filters = {
			"service_appointment": (
				appointment_names[0] if len(appointment_names) == 1 else ["in", appointment_names]
			),
			"allocation_status": "Held",
		}
		candidate_names = frappe.get_all("Service Resource Allocation", filters=filters, pluck="name")
		if not candidate_names:
			return 0
		_lock_allocation_rows(candidate_names)
		rows = frappe.get_all(
			"Service Resource Allocation",
			filters={**filters, "name": ["in", candidate_names]},
			fields=[
				"name",
				"service_appointment",
				"resource_type",
				"resource_reference",
				"allocation_date",
				"start_time",
				"end_time",
				"appointment_start_time",
				"appointment_end_time",
				"capacity_consumed",
				"buffer_before_minutes",
				"buffer_after_minutes",
			],
		)
		if not rows:
			return 0
		if len(appointment_names) == 2:
			_validate_couple_ledger_rows(appointment_names, rows)

		now = now_datetime()
		for row in rows:
			frappe.db.set_value(
				"Service Resource Allocation",
				row["name"],
				{"allocation_status": "Confirmed", "is_confirmed": 1, "confirmed_at": now},
				update_modified=False,
			)

		for appointment_name in appointment_names:
			_update_appointment_allocation_status(appointment_name, "Confirmed")
		if commit:
			frappe.db.commit()  # nosemgrep - caller requested an explicit transaction boundary.
		return len(rows)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def _validate_couple_ledger_rows(appointment_names: list[str], rows: list[dict[str, Any]]) -> None:
	for appointment_name in appointment_names:
		record = _get_appointment_couple_record(appointment_name)
		expected = sorted(
			_allocation_signature(row) for row in _expected_couple_allocation_rows(record, appointment_name)
		)
		actual = sorted(
			_allocation_signature(_prepare_allocation_payload(row))
			for row in rows
			if row.get("service_appointment") == appointment_name
		)
		if actual != expected:
			raise CapacityReservationError(
				_("Held allocations are incomplete for couple appointment {0}").format(appointment_name)
			)


def _reserve_appointment_allocation_groups(
	requests: list[dict[str, Any]],
	savepoint_prefix: str,
	commit: bool = False,
	couple_booking: bool = False,
) -> dict[str, list[str]]:
	"""Reserve one or more appointment allocation groups under one savepoint."""
	savepoint = _savepoint_name(savepoint_prefix)
	frappe.db.savepoint(savepoint)
	try:
		request_names = [request.get("appointment_name") for request in requests if isinstance(request, dict)]
		_lock_service_appointment_rows(request_names)
		if couple_booking:
			requests = _validate_couple_reservation_requests(requests)
		else:
			# Repeat the singleton guard after taking the appointment lock. A pair
			# link may have been committed while this reservation was waiting.
			for appointment_name in request_names:
				if frappe.db.get_value("Service Appointment", appointment_name, "couple_appointment_id"):
					raise CapacityReservationError(
						_("Couple appointments must reserve capacity through the atomic pair operation")
					)

		created_names = {request["appointment_name"]: [] for request in requests}
		prepared_requests = []
		for request in requests:
			prepared_requests.append(
				{
					**request,
					"prepared_allocations": [
						_prepare_allocation_payload(row) for row in request["allocations"]
					],
				}
			)

		if couple_booking:
			_validate_couple_prepared_allocations(prepared_requests)

		all_prepared = [row for request in prepared_requests for row in request["prepared_allocations"]]
		lock_counter_resource_rows(resources=all_prepared)
		_ensure_counter_rows(all_prepared)
		_apply_counter_deltas(all_prepared, direction="reserve")

		couple_metadata: dict[str, Any] = {}
		if couple_booking:
			couple_metadata = {
				"couple_booking": True,
				"couple_appointment_names": [request["appointment_name"] for request in prepared_requests],
				"reservation_group": savepoint,
			}

		# Counter updates for every appointment happen before the first ledger insert.
		for request in prepared_requests:
			appointment_name = request["appointment_name"]
			metadata = {
				"source": "booking_transaction_service",
				**request.get("extra_metadata", {}),
				**couple_metadata,
			}
			for row in request["prepared_allocations"]:
				doc = frappe.get_doc(
					{
						"doctype": "Service Resource Allocation",
						"allocation_date": row["allocation_date"],
						"service_appointment": appointment_name,
						"service_booking": request.get("booking_name"),
						"resource_type": row["resource_type"],
						"resource_reference": row["resource_reference"],
						"start_time": row["start_time"],
						"end_time": row["end_time"],
						"appointment_start_time": row["appointment_start_time"],
						"appointment_end_time": row["appointment_end_time"],
						"capacity_consumed": row["capacity_consumed"],
						"buffer_before_minutes": row["buffer_before_minutes"],
						"buffer_after_minutes": row["buffer_after_minutes"],
						"allocation_status": request["allocation_status"],
						"metadata_json": metadata,
					}
				)
				doc.insert(ignore_permissions=True)
				created_names[appointment_name].append(doc.name)

		# Statuses are updated only after both appointments have complete ledgers.
		for request in prepared_requests:
			_update_appointment_allocation_status(request["appointment_name"], request["allocation_status"])

		if commit:
			frappe.db.commit()
		return created_names
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def _validate_couple_reservation_requests(
	appointments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
	if not isinstance(appointments, list | tuple) or len(appointments) != 2:
		raise CapacityReservationError(_("A couple reservation requires exactly two appointments"))

	names = []
	for request in appointments:
		if not isinstance(request, dict) or not request.get("appointment_name"):
			raise CapacityReservationError(_("Each couple reservation requires an appointment_name"))
		names.append(str(request["appointment_name"]))

	names = _validate_couple_appointment_names(names)
	appointment_records = {name: _get_appointment_couple_record(name) for name in names}

	booking_ids = {record.get("booking_id") for record in appointment_records.values()}
	if len(booking_ids) != 1 or not next(iter(booking_ids), None):
		raise CapacityReservationError(_("Couple appointments must share the same booking ID"))

	appointment_dates = {getdate(record.get("appointment_date")) for record in appointment_records.values()}
	start_times = {_time_str(record.get("start_time")) for record in appointment_records.values()}
	if len(appointment_dates) != 1 or len(start_times) != 1:
		raise CapacityReservationError(_("Couple appointments must share the same start time"))

	primary_count = sum(cint(record.get("is_primary_in_couple")) for record in appointment_records.values())
	if primary_count != 1:
		raise CapacityReservationError(_("Couple appointments must identify exactly one primary appointment"))

	shared_units = {
		record.get("service_unit") for record in appointment_records.values() if record.get("service_unit")
	}
	if len(shared_units) == 1 and all(record.get("service_unit") for record in appointment_records.values()):
		shared_unit = next(iter(shared_units))
		unit = frappe.db.get_value("Service Unit", shared_unit, ["allow_overlap", "capacity"], as_dict=True)
		if not unit or not cint(unit.get("allow_overlap")) or flt(unit.get("capacity") or 1) < 2:
			raise CapacityReservationError(
				_("Shared couple service unit {0} does not allow two simultaneous services").format(
					shared_unit
				)
			)

	normalized = []
	statuses = set()
	for raw_request, appointment_name in zip(appointments, names, strict=True):
		allocations = raw_request.get("allocations")
		if not isinstance(allocations, list | tuple) or not allocations:
			raise CapacityReservationError(
				_("Couple appointment {0} requires allocation payloads").format(appointment_name)
			)
		if not any(row.get("resource_type") == "Service Provider" for row in allocations):
			raise CapacityReservationError(
				_("Couple appointment {0} requires a provider allocation").format(appointment_name)
			)

		record = appointment_records[appointment_name]
		booking_name = raw_request.get("booking_name") or record.get("booking_id")
		if booking_name != record.get("booking_id"):
			raise CapacityReservationError(
				_("Allocation booking must match appointment {0}'s booking ID").format(appointment_name)
			)

		allocation_status = raw_request.get("allocation_status") or "Held"
		if allocation_status not in ACTIVE_RESERVATION_STATUSES:
			raise CapacityReservationError(
				_("Unsupported active allocation status: {0}").format(allocation_status)
			)
		statuses.add(allocation_status)

		extra_metadata = raw_request.get("extra_metadata") or {}
		if not isinstance(extra_metadata, dict):
			raise CapacityReservationError(_("extra_metadata must be a dictionary"))

		normalized.append(
			{
				"appointment_name": appointment_name,
				"booking_name": booking_name,
				"allocations": list(allocations),
				"allocation_status": allocation_status,
				"extra_metadata": extra_metadata,
				"appointment_record": record,
			}
		)

	if len(statuses) != 1:
		raise CapacityReservationError(_("Both couple appointments must use the same allocation status"))

	return normalized


def _validate_couple_appointment_names(appointment_names: list[str]) -> list[str]:
	if not isinstance(appointment_names, list | tuple) or len(appointment_names) != 2:
		raise CapacityReservationError(_("Exactly two couple appointment names are required"))

	names = [str(name) for name in appointment_names if name]
	if len(names) != 2 or len(set(names)) != 2:
		raise CapacityReservationError(_("Couple appointment names must be present and distinct"))

	for name in names:
		if not frappe.db.exists("Service Appointment", name):
			raise CapacityReservationError(_("Service Appointment {0} not found").format(name))

	records = {name: _get_appointment_couple_record(name) for name in names}
	first, second = names
	if (
		records[first].get("couple_appointment_id") != second
		or records[second].get("couple_appointment_id") != first
	):
		raise CapacityReservationError(_("Couple appointment links must be reciprocal"))

	return names


def _get_appointment_couple_record(appointment_name: str) -> dict[str, Any]:
	record = frappe.db.get_value(
		"Service Appointment",
		appointment_name,
		[
			"booking_id",
			"appointment_type",
			"appointment_provider",
			"service_unit",
			"appointment_date",
			"start_time",
			"end_time",
			"couple_appointment_id",
			"is_primary_in_couple",
		],
		as_dict=True,
	)
	if not record:
		raise CapacityReservationError(_("Service Appointment {0} not found").format(appointment_name))
	return record


def _validate_couple_prepared_allocations(requests: list[dict[str, Any]]) -> None:
	for request in requests:
		record = request["appointment_record"]
		expected_date = getdate(record.get("appointment_date"))
		expected_start = _time_str(record.get("start_time"))
		expected_end = _time_str(record.get("end_time"))
		for row in request["prepared_allocations"]:
			if row["allocation_date"] != expected_date:
				raise CapacityReservationError(
					_("Allocation date must match couple appointment {0}").format(request["appointment_name"])
				)
			if row["appointment_start_time"] != expected_start:
				raise CapacityReservationError(
					_("Allocation start must match couple appointment {0}").format(
						request["appointment_name"]
					)
				)
			if row["appointment_end_time"] != expected_end:
				raise CapacityReservationError(
					_("Allocation end must match couple appointment {0}").format(request["appointment_name"])
				)

		expected_rows = _expected_couple_allocation_rows(record, request["appointment_name"])
		actual_signatures = sorted(_allocation_signature(row) for row in request["prepared_allocations"])
		expected_signatures = sorted(_allocation_signature(row) for row in expected_rows)
		if actual_signatures != expected_signatures:
			raise CapacityReservationError(
				_("Allocation resources, buffers, and capacity must match couple appointment {0}").format(
					request["appointment_name"]
				)
			)


def _expected_couple_allocation_rows(record: dict[str, Any], appointment_name: str) -> list[dict[str, Any]]:
	service_type = record.get("appointment_type")
	provider = record.get("appointment_provider")
	service_unit = record.get("service_unit")
	if not service_type or not provider:
		raise CapacityReservationError(
			_("Couple appointment {0} requires a service and provider").format(appointment_name)
		)
	if not frappe.db.exists(
		"Service Provider Service",
		{
			"parent": provider,
			"parenttype": "Service Provider",
			"service_type": service_type,
			"disabled": 0,
		},
	):
		raise CapacityReservationError(
			_("The assigned provider cannot offer couple appointment {0}'s service").format(appointment_name)
		)

	required_unit_types = frappe.get_all(
		"Service Type Unit Type",
		filters={"parent": service_type, "parenttype": "Service Type"},
		pluck="service_unit_type",
	)
	if required_unit_types and not service_unit:
		raise CapacityReservationError(
			_("Couple appointment {0} requires a service unit").format(appointment_name)
		)
	if not required_unit_types and service_unit:
		raise CapacityReservationError(
			_("Couple appointment {0}'s service does not use a service unit").format(appointment_name)
		)
	if service_unit:
		unit = frappe.db.get_value(
			"Service Unit",
			service_unit,
			["unit_type", "disabled", "allow_appointments"],
			as_dict=True,
		)
		if (
			not unit
			or cint(unit.get("disabled"))
			or not cint(unit.get("allow_appointments"))
			or unit.get("unit_type") not in required_unit_types
		):
			raise CapacityReservationError(
				_("Service unit is not eligible for couple appointment {0}").format(appointment_name)
			)

	service = (
		frappe.db.get_value("Service Type", service_type, ["buffer_before", "buffer_after"], as_dict=True)
		or {}
	)
	buffer_before = cint(service.get("buffer_before") or 0)
	buffer_after = cint(service.get("buffer_after") or 0)
	allocation_date = getdate(record.get("appointment_date"))
	appointment_start = datetime.combine(allocation_date, get_time(record.get("start_time")))
	appointment_end = datetime.combine(allocation_date, get_time(record.get("end_time")))
	allocation_start = appointment_start - timedelta(minutes=buffer_before)
	allocation_end = appointment_end + timedelta(minutes=buffer_after)
	if allocation_start.date() != allocation_date or (
		allocation_end.date() != allocation_date and allocation_end.time() != time(0, 0)
	):
		raise CapacityReservationError(_("Couple appointment buffers cannot cross calendar dates"))

	common = {
		"allocation_date": allocation_date,
		"start_time": allocation_start.time().strftime("%H:%M:%S"),
		"end_time": allocation_end.time().strftime("%H:%M:%S"),
		"appointment_start_time": _time_str(record.get("start_time")),
		"appointment_end_time": _time_str(record.get("end_time")),
		"capacity_consumed": 1.0,
		"buffer_before_minutes": buffer_before,
		"buffer_after_minutes": buffer_after,
	}
	rows = [
		{
			**common,
			"resource_type": "Service Provider",
			"resource_reference": provider,
		}
	]
	if service_unit:
		rows.append(
			{
				**common,
				"resource_type": "Service Unit",
				"resource_reference": service_unit,
			}
		)
	return rows


def _allocation_signature(row: dict[str, Any]) -> tuple:
	return (
		str(row.get("resource_type")),
		str(row.get("resource_reference")),
		str(getdate(row.get("allocation_date"))),
		_time_str(row.get("start_time")),
		_time_str(row.get("end_time")),
		_time_str(row.get("appointment_start_time")),
		_time_str(row.get("appointment_end_time")),
		round(flt(row.get("capacity_consumed")), 6),
		cint(row.get("buffer_before_minutes")),
		cint(row.get("buffer_after_minutes")),
	)


def _prepare_allocation_payload(payload: dict[str, Any]) -> dict[str, Any]:
	required = [
		"resource_type",
		"resource_reference",
		"allocation_date",
		"start_time",
		"end_time",
		"appointment_start_time",
		"appointment_end_time",
	]
	missing = [k for k in required if not payload.get(k)]
	if missing:
		raise CapacityReservationError(_("Missing allocation fields: {0}").format(", ".join(missing)))

	prepared = {
		"resource_type": payload["resource_type"],
		"resource_reference": payload["resource_reference"],
		"allocation_date": getdate(payload["allocation_date"]),
		"start_time": _time_str(payload["start_time"]),
		"end_time": _time_str(payload["end_time"]),
		"appointment_start_time": _time_str(payload["appointment_start_time"]),
		"appointment_end_time": _time_str(payload["appointment_end_time"]),
		"capacity_consumed": flt(payload.get("capacity_consumed") or 1.0),
		"buffer_before_minutes": cint(payload.get("buffer_before_minutes") or 0),
		"buffer_after_minutes": cint(payload.get("buffer_after_minutes") or 0),
	}
	if prepared["capacity_consumed"] <= 0:
		raise CapacityReservationError(_("capacity_consumed must be greater than zero"))

	return prepared


def _prepare_release_payload(payload: dict[str, Any]) -> dict[str, Any]:
	return {
		"resource_type": payload["resource_type"],
		"resource_reference": payload["resource_reference"],
		"allocation_date": getdate(payload["allocation_date"]),
		"start_time": _time_str(payload["start_time"]),
		"end_time": _time_str(payload["end_time"]),
		"capacity_consumed": flt(payload.get("capacity_consumed") or 1.0),
	}


def _ensure_counter_rows(prepared: list[dict[str, Any]]) -> None:
	"""Ensure relevant counter rows exist by rebuilding missing resource/date projections."""
	pairs = {(p["allocation_date"], p["resource_type"], p["resource_reference"]) for p in prepared}
	for allocation_date, resource_type, resource_reference in sorted(
		pairs, key=lambda pair: (str(pair[0]), str(pair[1]), str(pair[2]))
	):
		counter_exists = frappe.db.exists(
			"Resource Availability Counter",
			{
				"counter_date": allocation_date,
				"resource_type": resource_type,
				"resource_reference": resource_reference,
			},
		)
		if not counter_exists:
			rebuild_counter_for_date(
				counter_date=allocation_date,
				resource_type=resource_type,
				resource_reference=resource_reference,
			)


def _apply_counter_deltas(prepared: list[dict[str, Any]], direction: str) -> None:
	slot_size = _slot_size_minutes()
	if direction not in ("reserve", "release"):
		raise CapacityReservationError(_("Unsupported counter delta direction: {0}").format(direction))
	lock_counter_resource_rows(resources=prepared)

	# Aggregate first so a shared provider/unit counter is checked once for the
	# couple's full quantity. Lock ordering is then independent of guest ordering.
	delta_by_counter: dict[tuple[str, str, str, str], dict[str, Any]] = {}
	for row in prepared:
		slots = _slot_times_for_interval(
			row["allocation_date"], row["start_time"], row["end_time"], slot_size
		)
		for slot_time in slots:
			key = (
				str(row["allocation_date"]),
				str(row["resource_type"]),
				str(row["resource_reference"]),
				slot_time,
			)
			if key not in delta_by_counter:
				delta_by_counter[key] = {
					"counter_date": row["allocation_date"],
					"counter_slot_time": slot_time,
					"resource_type": row["resource_type"],
					"resource_reference": row["resource_reference"],
					"qty": 0.0,
				}
			delta_by_counter[key]["qty"] += row["capacity_consumed"]

	deltas = [delta_by_counter[key] for key in sorted(delta_by_counter)]

	# Lock the whole resource set before changing any counter. Concurrent couple
	# reservations therefore take locks in the same order and cannot partially win.
	for delta in deltas:
		frappe.db.sql(
			"""
			SELECT name
			FROM `tabResource Availability Counter`
			WHERE counter_date = %(counter_date)s
			  AND counter_slot_time = %(counter_slot_time)s
			  AND resource_type = %(resource_type)s
			  AND resource_reference = %(resource_reference)s
			FOR UPDATE
			""",
			delta,
		)

	for delta in deltas:
		if direction == "reserve":
			frappe.db.sql(
				"""
				UPDATE `tabResource Availability Counter`
				SET
					consumed_capacity = consumed_capacity + %(qty)s,
					remaining_capacity = remaining_capacity - %(qty)s
				WHERE counter_date = %(counter_date)s
				  AND counter_slot_time = %(counter_slot_time)s
				  AND resource_type = %(resource_type)s
				  AND resource_reference = %(resource_reference)s
				  AND is_blocked = 0
				  AND remaining_capacity >= %(qty)s
				""",
				delta,
			)
			if _last_sql_rowcount() == 0:
				raise CapacityReservationError(
					_("Insufficient capacity for {0} {1} on {2} at {3}").format(
						delta["resource_type"],
						delta["resource_reference"],
						delta["counter_date"],
						delta["counter_slot_time"],
					)
				)
		else:
			frappe.db.sql(
				"""
				UPDATE `tabResource Availability Counter`
				SET
					consumed_capacity = GREATEST(consumed_capacity - %(qty)s, 0),
					remaining_capacity = LEAST(remaining_capacity + %(qty)s, max_capacity)
				WHERE counter_date = %(counter_date)s
				  AND counter_slot_time = %(counter_slot_time)s
				  AND resource_type = %(resource_type)s
				  AND resource_reference = %(resource_reference)s
				""",
				delta,
			)


def _last_sql_rowcount() -> int:
	cursor = getattr(frappe.db, "_cursor", None)
	if cursor is None:
		return 0
	return int(getattr(cursor, "rowcount", 0) or 0)


def _slot_times_for_interval(
	allocation_date, start_time_str: str, end_time_str: str, slot_size: int
) -> list[str]:
	start_dt = datetime.combine(allocation_date, get_time(start_time_str))
	end_dt = datetime.combine(allocation_date, get_time(end_time_str))
	if end_dt <= start_dt:
		end_dt = end_dt + timedelta(days=1)

	day_start = datetime.combine(allocation_date, time(0, 0, 0))
	day_end = day_start + timedelta(days=1)
	clamped_start = max(day_start, start_dt)
	clamped_end = min(day_end, end_dt)
	if clamped_end <= clamped_start:
		return []

	step = timedelta(minutes=slot_size)
	from_midnight = int((clamped_start - day_start).total_seconds() // 60)
	slot_index = from_midnight // slot_size
	cursor = day_start + timedelta(minutes=slot_index * slot_size)

	result: list[str] = []
	while cursor < clamped_end:
		slot_end = cursor + step
		if slot_end > clamped_start and cursor < clamped_end:
			result.append(cursor.time().strftime("%H:%M:%S"))
		cursor += step
	return result


def _update_appointment_allocation_status(appointment_name: str, status: str) -> None:
	if frappe.db.exists("DocField", {"parent": "Service Appointment", "fieldname": "allocation_status"}):
		frappe.db.set_value(
			"Service Appointment",
			appointment_name,
			"allocation_status",
			status if status in ("Held", "Confirmed", "Released") else "Released",
			update_modified=False,
		)


def _time_str(value) -> str:
	return get_time(value).strftime("%H:%M:%S")


def _slot_size_minutes() -> int:
	return max(1, cint(frappe.db.get_single_value("Service Appointment Settings", "default_slot_size") or 15))


def _lock_service_appointment_rows(appointment_names: list[str]) -> None:
	names = sorted({str(name) for name in appointment_names if name})
	if not names:
		return
	frappe.db.sql(
		"""
		SELECT name
		FROM `tabService Appointment`
		WHERE name IN %(appointment_names)s
		ORDER BY name
		FOR UPDATE
		""",
		{"appointment_names": tuple(names)},
	)


def _lock_allocation_rows(allocation_names: list[str]) -> None:
	names = sorted({str(name) for name in allocation_names if name})
	if not names:
		return
	frappe.db.sql(
		"""
		SELECT name
		FROM `tabService Resource Allocation`
		WHERE name IN %(allocation_names)s
		ORDER BY name
		FOR UPDATE
		""",
		{"allocation_names": tuple(names)},
	)


def _savepoint_name(prefix: str) -> str:
	stamp = now_datetime().strftime("%H%M%S%f")
	return f"{prefix}_{stamp}"
