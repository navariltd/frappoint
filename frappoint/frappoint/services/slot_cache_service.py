import json

import frappe
from frappe.utils import add_days, getdate, nowdate

SLOT_CACHE_PREFIX = "booking_desk:slot_cache:v1"


def _cache():
	return frappe.cache()


def _to_date_string(value) -> str:
	return str(getdate(value))


def make_day_cache_key(service_type: str, date_value, duration: int) -> str:
	date_str = _to_date_string(date_value)
	return f"{SLOT_CACHE_PREFIX}:service:{service_type}:date:{date_str}:duration:{int(duration)}"


def _serialize(payload) -> str:
	return json.dumps(payload, separators=(",", ":"), default=str)


def _deserialize(payload: str):
	if not payload:
		return None
	try:
		return json.loads(payload)
	except Exception:
		return None


def _get_all_dates_for_window(days_ahead: int):
	start = getdate(nowdate())
	end = add_days(start, max(0, int(days_ahead or 0)))
	return [add_days(start, idx) for idx in range((end - start).days + 1)]


def _resolve_horizon_days(days_ahead=None) -> int:
	"""Resolve requested horizon using Service Appointment Settings.max_advance_days."""
	settings_horizon = int(
		frappe.db.get_single_value("Service Appointment Settings", "max_advance_days") or 30
	)

	if days_ahead in (None, ""):
		return settings_horizon

	try:
		requested_horizon = int(days_ahead)
	except (TypeError, ValueError):
		return settings_horizon

	if requested_horizon <= 0:
		return settings_horizon

	return min(requested_horizon, settings_horizon)


def _get_service_durations(service_type: str) -> list[int]:
	rows = frappe.get_all(
		"Service Type Price",
		filters={"parent": service_type},
		fields=["duration"],
	)
	durations = {int(row.duration) for row in rows if row.duration}
	if not durations:
		default_duration = frappe.db.get_value("Service Type", service_type, "default_duration_in_minutes")
		if default_duration:
			durations.add(int(default_duration))
	return sorted(durations)


def _get_provider_genders(provider_names: list[str]) -> dict[str, str]:
	if not provider_names:
		return {}
	rows = frappe.get_all(
		"Service Provider",
		filters={"name": ["in", list(set(provider_names))]},
		fields=["name", "gender"],
	)
	return {row.name: (row.gender or "") for row in rows}


def _filter_slots_payload(payload, provider=None, gender=None):
	if not payload:
		return []

	provider = (provider or "").strip()
	gender = (gender or "").strip()

	if not provider and not gender:
		return payload

	provider_genders = {}
	if gender:
		provider_names = []
		for day_group in payload:
			for slot in day_group.get("slots", []):
				for provider_row in slot.get("providers", []):
					provider_names.append(provider_row.get("provider"))
		provider_genders = _get_provider_genders(provider_names)

	filtered_days = []
	for day_group in payload:
		filtered_slots = []
		for slot in day_group.get("slots", []):
			providers = []
			for provider_row in slot.get("providers", []):
				provider_name = provider_row.get("provider")
				if provider and provider_name != provider:
					continue
				if gender:
					provider_gender = provider_genders.get(provider_name, "")
					if provider_gender != gender:
						continue
				providers.append(provider_row)

			if providers:
				updated_slot = dict(slot)
				updated_slot["providers"] = providers
				filtered_slots.append(updated_slot)

		if filtered_slots:
			filtered_days.append({"date": day_group.get("date"), "slots": filtered_slots})

	return filtered_days


def get_cached_available_slots(
	appointment_type: str,
	duration: int,
	provider=None,
	date=None,
	gender=None,
	days_ahead=None,
	compute_day_fn=None,
):
	"""
	Redis-first availability resolver.

	`compute_day_fn` must return payload in format_available_slots format for exactly one date.
	"""
	if not compute_day_fn:
		return []

	duration = int(duration)
	cache = _cache()

	if date:
		target_dates = [getdate(date)]
	else:
		target_dates = _get_all_dates_for_window(_resolve_horizon_days(days_ahead))

	results = []
	for target_date in target_dates:
		key = make_day_cache_key(appointment_type, target_date, duration)
		cached = _deserialize(cache.get_value(key))

		if cached is None:
			computed = compute_day_fn(target_date)
			computed = computed or []
			cache.set_value(key, _serialize(computed))
			cached = computed

		filtered = _filter_slots_payload(cached, provider=provider, gender=gender)
		if filtered:
			results.extend(filtered)

	return results


def warm_slot_cache_for_day(service_type: str, date_value, duration: int, compute_day_fn):
	payload = compute_day_fn(getdate(date_value)) or []
	_cache().set_value(
		make_day_cache_key(service_type, date_value, duration),
		_serialize(payload),
	)
	return payload


def warm_slot_cache_for_service_date(service_type: str, date_value, compute_day_fn):
	for duration in _get_service_durations(service_type):
		warm_slot_cache_for_day(service_type, date_value, duration, compute_day_fn)


def invalidate_service_date_cache(service_type: str, date_value):
	cache = _cache()
	for duration in _get_service_durations(service_type):
		cache.delete_value(make_day_cache_key(service_type, date_value, duration))


def invalidate_service_date_range_cache(service_type: str, start_date, end_date):
	start = getdate(start_date)
	end = getdate(end_date)
	for idx in range((end - start).days + 1):
		invalidate_service_date_cache(service_type, add_days(start, idx))


def _get_provider_service_types(provider: str) -> list[str]:
	return frappe.get_all(
		"Service Provider Service",
		filters={"parent": provider, "disabled": 0},
		pluck="service_type",
	)


def invalidate_provider_date_range_cache(provider: str, start_date, end_date):
	if not provider:
		return

	service_types = _get_provider_service_types(provider)
	if not service_types:
		return

	for service_type in service_types:
		invalidate_service_date_range_cache(service_type, start_date, end_date)


def _run_after_commit(func):
	"""
	Schedule *func* to run after the current DB transaction commits.

	Frappe exposes ``frappe.db.after_commit`` as a plain list (``append``),
	but some community builds expose it as a set (``add``).  We try both so
	that invalidation is always deferred instead of firing mid-transaction.
	If neither interface is present we fall back to an immediate call — the
	caller should be aware that this means stale-cache windows are possible
	on unsupported Frappe builds.
	"""
	after_commit = getattr(frappe.db, "after_commit", None)
	if after_commit is not None:
		if hasattr(after_commit, "append"):
			after_commit.append(func)
			return
		if hasattr(after_commit, "add"):
			after_commit.add(func)
			return
	# Last-resort: fire immediately.  This can produce a brief stale-cache
	# window on Frappe builds that don't expose after_commit.
	func()


def invalidate_on_appointment_mutation(appointment_doc):
	if not appointment_doc:
		return

	service_type = appointment_doc.get("appointment_type")
	appointment_date = appointment_doc.get("appointment_date")
	if not service_type or not appointment_date:
		return

	_run_after_commit(lambda: invalidate_service_date_cache(service_type, appointment_date))


def queue_warm_service_date(service_type: str, date_value):
	"""Small async warm-up for surgically invalidated dates."""
	if not service_type or not date_value:
		return

	frappe.enqueue(
		"frappoint.frappoint.services.slot_cache_service.warm_service_date_cache_job",
		service_type=service_type,
		date_value=str(getdate(date_value)),
		queue="short",
		is_async=True,
		now=False,
	)


def warm_service_date_cache_job(service_type: str, date_value: str):
	from ..doctype.service_provider_appointment_slot.service_provider_appointment_slot import (
		_get_available_slots_db,
	)

	date_obj = getdate(date_value)
	for duration in _get_service_durations(service_type):

		def _compute_day(day_date, current_duration=duration):
			return _get_available_slots_db(
				appointment_type=service_type,
				duration=current_duration,
				provider=None,
				date=day_date,
				gender=None,
				days_ahead=0,
			)

		warm_slot_cache_for_day(
			service_type=service_type,
			date_value=date_obj,
			duration=duration,
			compute_day_fn=_compute_day,
		)


def enqueue_nightly_slot_cache_pregeneration(horizon_days: int | None = None):
	frappe.enqueue(
		"frappoint.frappoint.services.slot_cache_service.nightly_slot_cache_pregeneration",
		horizon_days=horizon_days,
		queue="long",
		is_async=True,
		now=False,
	)


def nightly_slot_cache_pregeneration(horizon_days: int | None = None):
	"""
	Nightly batch cache warm job.
	By default follows Service Appointment Settings.max_advance_days.
	"""
	settings_horizon = int(
		frappe.db.get_single_value("Service Appointment Settings", "max_advance_days") or 30
	)
	horizon = int(horizon_days or settings_horizon)

	services = frappe.get_all("Service Type", filters={"disabled": 0}, pluck="name")
	if not services:
		return

	start = getdate(nowdate())
	end = add_days(start, max(0, horizon))

	for service_type in services:
		durations = _get_service_durations(service_type)
		if not durations:
			continue

		for idx in range((end - start).days + 1):
			day_date = add_days(start, idx)
			for duration in durations:
				payload = frappe.get_attr(
					"frappoint.frappoint.doctype.service_provider_appointment_slot.service_provider_appointment_slot._get_available_slots_db"
				)(
					appointment_type=service_type,
					duration=duration,
					provider=None,
					date=day_date,
					gender=None,
					days_ahead=0,
				)
				_cache().set_value(
					make_day_cache_key(service_type, day_date, duration),
					_serialize(payload or []),
				)


def purge_slot_cache_before_date(cutoff_date):
	"""
	Best-effort stale cache cleanup.
	Removes cache entries for dates older than cutoff.
	"""
	cache = _cache()
	try:
		cutoff = getdate(cutoff_date)
	except Exception:
		return

	try:
		keys = cache.get_keys(f"{SLOT_CACHE_PREFIX}:service:*")
	except Exception:
		# get_keys is implementation-specific; if unavailable, skip cleanup.
		return

	for key in keys:
		parts = key.split(":")
		try:
			date_idx = parts.index("date") + 1
			key_date = getdate(parts[date_idx])
		except Exception:
			continue

		if key_date < cutoff:
			cache.delete_value(key)


def lock_provider_date(provider: str, date_value):
	"""
	Optional Redis mutex helper for hot provider/date writes.
	This is advisory; DB row locks remain the correctness guardrail.
	"""
	date_str = _to_date_string(date_value)
	lock_name = f"{SLOT_CACHE_PREFIX}:lock:provider:{provider}:date:{date_str}"
	try:
		return _cache().lock(lock_name, timeout=8)
	except Exception:
		return None
