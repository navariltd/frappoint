import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate

from ..doctype.service_provider_appointment_slot.service_provider_appointment_slot import (
	format_available_slots,
)
from ..services.availability_projector import (
	get_available_slots as get_projected_available_slots,
)
from ..services.availability_projector import (
	get_couple_available_slots as get_projected_couple_available_slots,
)


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_available_dates(
	service_type: str | None = None,
	duration: int | str | None = None,
	provider: str | None = None,
	gender: str | None = None,
	days_ahead: int | str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	service_type_1: str | None = None,
	service_type_2: str | None = None,
	duration_1: int | str | None = None,
	duration_2: int | str | None = None,
	provider_1: str | None = None,
	provider_2: str | None = None,
	service_unit_1: str | None = None,
	service_unit_2: str | None = None,
	gender_1: str | None = None,
	gender_2: str | None = None,
	exclude_appointment_id_1: str | None = None,
	exclude_appointment_id_2: str | None = None,
):
	"""
	Get dates that have availability
	Use case: Calendar view, date picker
	"""
	if _is_couple_request(service_type_1, service_type_2):
		return get_couple_available_dates(
			service_type_1=service_type_1 or service_type,
			service_type_2=service_type_2,
			duration_1=duration_1 if duration_1 is not None else duration,
			duration_2=duration_2,
			provider_1=provider_1 or provider,
			provider_2=provider_2,
			service_unit_1=service_unit_1,
			service_unit_2=service_unit_2,
			gender_1=gender_1 or gender,
			gender_2=gender_2 or gender,
			exclude_appointment_id_1=exclude_appointment_id_1,
			exclude_appointment_id_2=exclude_appointment_id_2,
			days_ahead=days_ahead,
			start_date=start_date,
			end_date=end_date,
		)

	service_type = _normalize_service_type(service_type or service_type_1)
	if not service_type:
		return []

	duration = _resolve_duration(service_type, duration)
	if duration <= 0:
		return []

	range_start, range_end = _resolve_date_range(
		days_ahead=days_ahead,
		start_date=start_date,
		end_date=end_date,
	)
	rows = get_projected_available_slots(
		service_type_id=service_type,
		start_date=range_start,
		end_date=range_end,
		provider_id=provider,
		required_duration_minutes=duration,
	)
	rows = _filter_all_day_provider_unavailability(rows)

	if gender:
		gender_by_provider = {
			row["name"]: row["gender"]
			for row in frappe.get_all(
				"Service Provider",
				filters={"gender": gender},
				fields=["name", "gender"],
			)
		}
		rows = [r for r in rows if r.get("provider") in gender_by_provider]

	return sorted({str(row.get("date")) for row in rows if row.get("date")})


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_available_time_slots(
	service_type: str | None = None,
	duration: int | str | None = None,
	provider: str | None = None,
	date: str | None = None,
	gender: str | None = None,
	days_ahead: int | str | None = None,
	use_counter_engine: int | str | bool | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	service_type_1: str | None = None,
	service_type_2: str | None = None,
	duration_1: int | str | None = None,
	duration_2: int | str | None = None,
	provider_1: str | None = None,
	provider_2: str | None = None,
	service_unit_1: str | None = None,
	service_unit_2: str | None = None,
	gender_1: str | None = None,
	gender_2: str | None = None,
	exclude_appointment_id_1: str | None = None,
	exclude_appointment_id_2: str | None = None,
):
	"""
	Get available time slots
	Use case: Main booking interface
	"""
	if _is_couple_request(service_type_1, service_type_2):
		return get_couple_available_time_slots(
			service_type_1=service_type_1 or service_type,
			service_type_2=service_type_2,
			duration_1=duration_1 if duration_1 is not None else duration,
			duration_2=duration_2,
			provider_1=provider_1 or provider,
			provider_2=provider_2,
			service_unit_1=service_unit_1,
			service_unit_2=service_unit_2,
			date=date,
			gender_1=gender_1 or gender,
			gender_2=gender_2 or gender,
			exclude_appointment_id_1=exclude_appointment_id_1,
			exclude_appointment_id_2=exclude_appointment_id_2,
			days_ahead=days_ahead,
			use_counter_engine=use_counter_engine,
			start_date=start_date,
			end_date=end_date,
		)

	service_type = _normalize_service_type(service_type or service_type_1)
	if not service_type:
		return []

	duration = _resolve_duration(service_type, duration)
	if duration <= 0:
		return []

	# Availability search is projector-only. The legacy slot engine is no longer used here.
	_validate_counter_engine(use_counter_engine)

	range_start, range_end = _resolve_date_range(
		date=date,
		days_ahead=days_ahead,
		start_date=start_date,
		end_date=end_date,
	)
	rows = get_projected_available_slots(
		service_type_id=service_type,
		start_date=range_start,
		end_date=range_end,
		provider_id=provider,
		required_duration_minutes=duration,
	)

	if gender:
		provider_ids = [r.get("provider") for r in rows if r.get("provider")]
		allowed = set(
			frappe.get_all(
				"Service Provider",
				filters={"name": ["in", provider_ids], "gender": gender},
				pluck="name",
			)
		)
		rows = [r for r in rows if r.get("provider") in allowed]

	if date:
		target = str(getdate(date))
		rows = [r for r in rows if str(r.get("date")) == target]
	return format_available_slots(rows)


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_couple_available_dates(
	service_type_1: str,
	service_type_2: str,
	provider_1: str | None = None,
	provider_2: str | None = None,
	duration_1: int | str | None = None,
	duration_2: int | str | None = None,
	service_unit_1: str | None = None,
	service_unit_2: str | None = None,
	gender_1: str | None = None,
	gender_2: str | None = None,
	days_ahead: int | str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	exclude_appointment_id_1: str | None = None,
	exclude_appointment_id_2: str | None = None,
):
	"""Return dates on which both couple services can start together."""
	service_type_1 = _normalize_service_type(service_type_1)
	service_type_2 = _normalize_service_type(service_type_2)
	if not service_type_1 or not service_type_2:
		return []

	duration_1 = _resolve_duration(service_type_1, duration_1)
	duration_2 = _resolve_duration(service_type_2, duration_2)
	if duration_1 <= 0 or duration_2 <= 0:
		return []

	range_start, range_end = _resolve_date_range(
		days_ahead=days_ahead,
		start_date=start_date,
		end_date=end_date,
	)
	rows = get_projected_couple_available_slots(
		service_type_1=service_type_1,
		service_type_2=service_type_2,
		start_date=range_start,
		end_date=range_end,
		provider_1=_normalize_optional_id(provider_1),
		provider_2=_normalize_optional_id(provider_2),
		service_unit_1=_normalize_optional_id(service_unit_1),
		service_unit_2=_normalize_optional_id(service_unit_2),
		duration_1=duration_1,
		duration_2=duration_2,
		exclude_appointment_id_1=_normalize_optional_id(exclude_appointment_id_1),
		exclude_appointment_id_2=_normalize_optional_id(exclude_appointment_id_2),
	)
	rows = _filter_couple_all_day_provider_unavailability(rows)
	rows = _filter_couple_provider_gender(rows, gender_1, gender_2)
	return sorted({str(row.get("date")) for row in rows if row.get("date")})


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_couple_available_time_slots(
	service_type_1: str,
	service_type_2: str,
	provider_1: str | None = None,
	provider_2: str | None = None,
	duration_1: int | str | None = None,
	duration_2: int | str | None = None,
	service_unit_1: str | None = None,
	service_unit_2: str | None = None,
	date: str | None = None,
	gender_1: str | None = None,
	gender_2: str | None = None,
	days_ahead: int | str | None = None,
	use_counter_engine: int | str | bool | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	exclude_appointment_id_1: str | None = None,
	exclude_appointment_id_2: str | None = None,
):
	"""Return provider/unit pair candidates for simultaneous couple services."""
	service_type_1 = _normalize_service_type(service_type_1)
	service_type_2 = _normalize_service_type(service_type_2)
	if not service_type_1 or not service_type_2:
		return []

	duration_1 = _resolve_duration(service_type_1, duration_1)
	duration_2 = _resolve_duration(service_type_2, duration_2)
	if duration_1 <= 0 or duration_2 <= 0:
		return []

	_validate_counter_engine(use_counter_engine)
	range_start, range_end = _resolve_date_range(
		date=date,
		days_ahead=days_ahead,
		start_date=start_date,
		end_date=end_date,
	)
	rows = get_projected_couple_available_slots(
		service_type_1=service_type_1,
		service_type_2=service_type_2,
		start_date=range_start,
		end_date=range_end,
		provider_1=_normalize_optional_id(provider_1),
		provider_2=_normalize_optional_id(provider_2),
		service_unit_1=_normalize_optional_id(service_unit_1),
		service_unit_2=_normalize_optional_id(service_unit_2),
		duration_1=duration_1,
		duration_2=duration_2,
		exclude_appointment_id_1=_normalize_optional_id(exclude_appointment_id_1),
		exclude_appointment_id_2=_normalize_optional_id(exclude_appointment_id_2),
	)
	rows = _filter_couple_all_day_provider_unavailability(rows)
	rows = _filter_couple_provider_gender(rows, gender_1, gender_2)
	if date:
		target = str(getdate(date))
		rows = [row for row in rows if str(row.get("date")) == target]
	return _format_couple_available_slots(rows)


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def check_slot_availability(slot_ids: str | list):
	"""
	Check if specific slots are still available before booking
	Use case: Pre-booking validation
	"""
	frappe.throw(_("Legacy slot availability precheck has been removed. Use allocation/counter APIs."))


def _resolve_date_range(
	date: str | None = None,
	days_ahead: int | str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
):
	if date:
		target = getdate(date)
		return target, target
	if start_date or end_date:
		start = getdate(start_date or nowdate())
		end = getdate(end_date or start)
		return (end, start) if end < start else (start, end)

	start = getdate(nowdate())
	settings_days = frappe.db.get_single_value("Service Appointment Settings", "max_advance_days") or 30
	effective_days = cint_safe(days_ahead)
	if effective_days <= 0:
		effective_days = cint_safe(settings_days)

	return start, add_days(start, effective_days)


def _validate_counter_engine(use_counter_engine) -> None:
	use_counter_engine = cint_safe(use_counter_engine if use_counter_engine is not None else 1) == 1
	if not use_counter_engine:
		frappe.throw(_("Legacy slot availability engine has been removed. Use the counter engine."))


def _is_couple_request(service_type_1, service_type_2) -> bool:
	return service_type_1 is not None or service_type_2 is not None


def cint_safe(value) -> int:
	try:
		return int(value)
	except Exception:
		return 0


def _normalize_service_type(service_type):
	if service_type is None:
		return None

	value = str(service_type).strip()
	if not value or value.lower() in {"null", "undefined", "[object object]"}:
		return None

	return value


def _normalize_optional_id(value):
	return _normalize_service_type(value)


def _resolve_duration(service_type: str, duration) -> int:
	parsed = cint_safe(duration)
	if parsed > 0:
		return parsed

	default_duration = frappe.db.get_value("Service Type", service_type, "default_duration_in_minutes") or 0
	return cint_safe(default_duration)


def _filter_all_day_provider_unavailability(rows):
	if not rows or not frappe.db.table_exists("Service Provider Unavailability"):
		return rows

	provider_ids = sorted({row.get("provider") for row in rows if row.get("provider")})
	if not provider_ids:
		return rows

	dates = [getdate(row.get("date")) for row in rows if row.get("date")]
	if not dates:
		return rows

	unavailability_rows = frappe.get_all(
		"Service Provider Unavailability",
		filters={
			"provider": ["in", provider_ids],
			"status": "Active",
			"docstatus": 1,
			"all_day": 1,
			"from_date": ["<=", max(dates)],
			"to_date": [">=", min(dates)],
		},
		fields=["provider", "from_date", "to_date"],
	)
	if not unavailability_rows:
		return rows

	target_dates = sorted(set(dates))
	blocked_provider_dates = set()
	for unavailable in unavailability_rows:
		from_date = getdate(unavailable.from_date)
		to_date = getdate(unavailable.to_date)
		for target_date in target_dates:
			if from_date <= target_date <= to_date:
				blocked_provider_dates.add((unavailable.provider, target_date))

	return [
		row for row in rows if (row.get("provider"), getdate(row.get("date"))) not in blocked_provider_dates
	]


def _filter_couple_all_day_provider_unavailability(rows):
	if not rows:
		return rows

	leg_rows = []
	for index, row in enumerate(rows):
		for leg_name in ("guest_1", "guest_2"):
			leg = row.get(leg_name) or {}
			if leg.get("provider") and row.get("date"):
				leg_rows.append(
					{
						"provider": leg.get("provider"),
						"date": row.get("date"),
						"couple_row_index": index,
						"couple_leg": leg_name,
					}
				)

	filtered_legs = _filter_all_day_provider_unavailability(leg_rows)
	allowed_legs = {
		(row["couple_row_index"], row["couple_leg"])
		for row in filtered_legs
		if row.get("couple_row_index") is not None
	}
	return [
		row
		for index, row in enumerate(rows)
		if (index, "guest_1") in allowed_legs and (index, "guest_2") in allowed_legs
	]


def _filter_couple_provider_gender(rows, gender_1=None, gender_2=None):
	filtered = rows
	for leg_name, gender in (("guest_1", gender_1), ("guest_2", gender_2)):
		if not gender or not filtered:
			continue
		provider_ids = sorted(
			{
				row.get(leg_name, {}).get("provider")
				for row in filtered
				if row.get(leg_name, {}).get("provider")
			}
		)
		allowed = set(
			frappe.get_all(
				"Service Provider",
				filters={"name": ["in", provider_ids], "gender": gender},
				pluck="name",
			)
		)
		filtered = [row for row in filtered if row.get(leg_name, {}).get("provider") in allowed]
	return filtered


def _format_couple_available_slots(rows):
	by_date: dict[str, list[dict]] = {}
	for row in rows:
		date_str = str(row.get("date"))
		serialized = dict(row)
		serialized["date"] = date_str
		for time_field in ("start_time", "end_time", "end_time_1", "end_time_2"):
			if serialized.get(time_field) is not None:
				serialized[time_field] = str(serialized[time_field])
		serialized["guest_1"] = _serialize_couple_guest(row.get("guest_1") or {})
		serialized["guest_2"] = _serialize_couple_guest(row.get("guest_2") or {})
		by_date.setdefault(date_str, []).append(serialized)

	return [
		{
			"date": date_str,
			"slots": sorted(
				by_date[date_str],
				key=lambda row: (
					row.get("start_time") or "",
					row.get("provider_name_1") or row.get("provider_1") or "",
					row.get("provider_name_2") or row.get("provider_2") or "",
				),
			),
		}
		for date_str in sorted(by_date)
	]


def _serialize_couple_guest(guest):
	serialized = dict(guest)
	if serialized.get("date") is not None:
		serialized["date"] = str(serialized["date"])
	for time_field in ("start_time", "end_time"):
		if serialized.get(time_field) is not None:
			serialized[time_field] = str(serialized[time_field])
	return serialized
