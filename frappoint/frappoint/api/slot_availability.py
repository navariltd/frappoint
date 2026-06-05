import frappe
from frappe.utils import add_days, getdate, nowdate

from ..doctype.service_provider_appointment_slot.service_provider_appointment_slot import (
	format_available_slots,
)
from ..services.availability_projector import get_available_slots as get_projected_available_slots


@frappe.whitelist(allow_guest=True)
def get_available_dates(
	service_type: str,
	duration: int,
	provider: str | None = None,
	gender: str | None = None,
	days_ahead: int | str | None = None,
):
	"""
	Get dates that have availability
	Use case: Calendar view, date picker
	"""
	service_type = _normalize_service_type(service_type)
	if not service_type:
		return []

	duration = _resolve_duration(service_type, duration)
	if duration <= 0:
		return []

	start_date, end_date = _resolve_date_range(days_ahead=days_ahead)
	rows = get_projected_available_slots(
		service_type_id=service_type,
		start_date=start_date,
		end_date=end_date,
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


@frappe.whitelist(allow_guest=True)
def get_available_time_slots(
	service_type,
	duration,
	provider=None,
	date=None,
	gender=None,
	days_ahead=None,
	use_counter_engine=None,
):
	"""
	Get available time slots
	Use case: Main booking interface
	"""
	service_type = _normalize_service_type(service_type)
	if not service_type:
		return []

	duration = _resolve_duration(service_type, duration)
	if duration <= 0:
		return []

	# Availability search is projector-only. The legacy slot engine is no longer used here.
	use_counter_engine = cint_safe(use_counter_engine if use_counter_engine is not None else 1) == 1
	if not use_counter_engine:
		frappe.throw("Legacy slot availability engine has been removed. Use the counter engine.")

	start_date, end_date = _resolve_date_range(date=date, days_ahead=days_ahead)
	rows = get_projected_available_slots(
		service_type_id=service_type,
		start_date=start_date,
		end_date=end_date,
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


@frappe.whitelist(allow_guest=True)
def check_slot_availability(slot_ids):
	"""
	Check if specific slots are still available before booking
	Use case: Pre-booking validation
	"""
	frappe.throw("Legacy slot availability precheck has been removed. Use allocation/counter APIs.")


def _resolve_date_range(date: str | None = None, days_ahead: int | str | None = None):
	if date:
		target = getdate(date)
		return target, target

	start = getdate(nowdate())
	settings_days = frappe.db.get_single_value("Service Appointment Settings", "max_advance_days") or 30
	effective_days = cint_safe(days_ahead)
	if effective_days <= 0:
		effective_days = cint_safe(settings_days)

	return start, add_days(start, effective_days)


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
