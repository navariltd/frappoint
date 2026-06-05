from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate

ACTIVE_APPOINTMENT_STATUSES = ("Open", "Pending Payment", "Confirmed", "Checked In", "In Progress")
ROLLING_WINDOW_DAYS = 90


def select_provider_for_assignment(
	available_options,
	appointment_date=None,
	service_type: str | None = None,
	preferred_gender: str | None = None,
	exclude_provider: str | None = None,
) -> dict[str, Any] | None:
	"""Select the fairest provider from availability options.

	The ranking intentionally avoids alphabetical/provider-name order until every
	meaningful load metric is tied.
	"""
	options = normalize_provider_options(available_options)
	if exclude_provider:
		options = [row for row in options if row.get("provider") != exclude_provider]
	if not options:
		return None

	provider_ids = sorted({row["provider"] for row in options if row.get("provider")})
	provider_meta = _get_provider_metadata(provider_ids)

	if preferred_gender:
		gender = str(preferred_gender).strip()
		gender_matched = [
			row
			for row in options
			if _same_gender(provider_meta.get(row.get("provider"), {}).get("gender"), gender)
		]
		if not gender_matched:
			return None
		options = gender_matched

	metrics = _get_provider_load_metrics(
		provider_ids=[row["provider"] for row in options],
		appointment_date=appointment_date,
		service_type=service_type,
	)

	ranked = []
	for row in options:
		provider = row["provider"]
		meta = provider_meta.get(provider, {})
		load = metrics.get(provider, {})
		ranked.append(
			{
				**row,
				"provider_name": row.get("provider_name") or meta.get("provider_name") or provider,
				"gender": meta.get("gender"),
				"assignment_rank": {
					"day_count": load.get("day_count", 0),
					"service_window_count": load.get("service_window_count", 0),
					"overall_window_count": load.get("overall_window_count", 0),
					"last_assigned_at": load.get("last_assigned_at"),
				},
			}
		)

	ranked.sort(key=_assignment_sort_key)
	return ranked[0] if ranked else None


def rank_provider_options(
	available_options,
	appointment_date=None,
	service_type: str | None = None,
	preferred_gender: str | None = None,
	exclude_provider: str | None = None,
) -> list[dict[str, Any]]:
	"""Return all options ordered by the same fairness rule used for selection."""
	options = normalize_provider_options(available_options)
	if exclude_provider:
		options = [row for row in options if row.get("provider") != exclude_provider]
	if not options:
		return []

	selected = select_provider_for_assignment(
		options,
		appointment_date=appointment_date,
		service_type=service_type,
		preferred_gender=preferred_gender,
	)
	if not selected:
		return []

	provider_ids = sorted({row["provider"] for row in options if row.get("provider")})
	provider_meta = _get_provider_metadata(provider_ids)
	if preferred_gender:
		options = [
			row
			for row in options
			if _same_gender(
				provider_meta.get(row.get("provider"), {}).get("gender"),
				str(preferred_gender).strip(),
			)
		]

	metrics = _get_provider_load_metrics(
		provider_ids=[row["provider"] for row in options],
		appointment_date=appointment_date,
		service_type=service_type,
	)
	ranked = []
	for row in options:
		provider = row["provider"]
		meta = provider_meta.get(provider, {})
		load = metrics.get(provider, {})
		ranked.append(
			{
				**row,
				"provider_name": row.get("provider_name") or meta.get("provider_name") or provider,
				"gender": meta.get("gender"),
				"assignment_rank": {
					"day_count": load.get("day_count", 0),
					"service_window_count": load.get("service_window_count", 0),
					"overall_window_count": load.get("overall_window_count", 0),
					"last_assigned_at": load.get("last_assigned_at"),
				},
			}
		)
	ranked.sort(key=_assignment_sort_key)
	return ranked


def normalize_provider_options(value) -> list[dict[str, Any]]:
	if not value:
		return []
	if isinstance(value, str):
		try:
			value = json.loads(value)
		except Exception:
			return []

	seen = set()
	options = []
	for raw in value or []:
		row = frappe._dict(raw or {})
		provider = row.get("provider") or row.get("appointment_provider")
		if not provider:
			continue

		service_unit = row.get("service_unit") or row.get("serviceUnit")
		key = (provider, service_unit or "")
		if key in seen:
			continue
		seen.add(key)

		slot_ids = row.get("slot_ids") or row.get("slotIds") or []
		options.append(
			{
				"provider": provider,
				"provider_name": row.get("provider_name") or row.get("providerName"),
				"service_unit": service_unit,
				"service_unit_name": row.get("service_unit_name") or row.get("serviceUnitName"),
				"slot_ids": slot_ids if isinstance(slot_ids, list) else [],
				"shift_assignment": row.get("shift_assignment") or row.get("shiftAssignment"),
			}
		)

	return options


def _assignment_sort_key(row: dict[str, Any]):
	rank = row.get("assignment_rank") or {}
	last_assigned_at = rank.get("last_assigned_at")
	last_key = get_datetime(last_assigned_at) if last_assigned_at else get_datetime("1900-01-01")
	return (
		int(rank.get("day_count") or 0),
		int(rank.get("service_window_count") or 0),
		int(rank.get("overall_window_count") or 0),
		last_key,
		str(row.get("provider_name") or row.get("provider") or "").lower(),
		str(row.get("provider") or ""),
		str(row.get("service_unit") or ""),
	)


def _get_provider_metadata(provider_ids: list[str]) -> dict[str, dict[str, Any]]:
	if not provider_ids:
		return {}

	rows = frappe.get_all(
		"Service Provider",
		filters={"name": ["in", provider_ids], "active": 1},
		fields=["name", "provider_name", "gender"],
	)
	return {row["name"]: row for row in rows}


def _get_provider_load_metrics(
	provider_ids: list[str],
	appointment_date=None,
	service_type: str | None = None,
) -> dict[str, dict[str, Any]]:
	provider_ids = sorted({provider for provider in provider_ids if provider})
	if not provider_ids:
		return {}
	provider_tuple = tuple(provider_ids)

	metrics = {
		provider: {
			"day_count": 0,
			"service_window_count": 0,
			"overall_window_count": 0,
			"last_assigned_at": None,
		}
		for provider in provider_ids
	}

	target_date = getdate(appointment_date) if appointment_date else getdate()
	window_start = target_date - timedelta(days=ROLLING_WINDOW_DAYS)
	window_end = target_date + timedelta(days=ROLLING_WINDOW_DAYS)

	day_rows = frappe.db.sql(
		"""
		SELECT appointment_provider, COUNT(*) AS appointment_count
		FROM `tabService Appointment`
		WHERE appointment_provider IN %(providers)s
		  AND appointment_date = %(appointment_date)s
		  AND status IN %(active_statuses)s
		  AND docstatus != 2
		GROUP BY appointment_provider
		""",
		{
			"providers": provider_tuple,
			"appointment_date": target_date,
			"active_statuses": ACTIVE_APPOINTMENT_STATUSES,
		},
		as_dict=True,
	)
	for row in day_rows:
		metrics[row["appointment_provider"]]["day_count"] = int(row["appointment_count"] or 0)

	overall_rows = frappe.db.sql(
		"""
		SELECT appointment_provider, COUNT(*) AS appointment_count, MAX(creation) AS last_assigned_at
		FROM `tabService Appointment`
		WHERE appointment_provider IN %(providers)s
		  AND appointment_date BETWEEN %(window_start)s AND %(window_end)s
		  AND status IN %(active_statuses)s
		  AND docstatus != 2
		GROUP BY appointment_provider
		""",
		{
			"providers": provider_tuple,
			"window_start": window_start,
			"window_end": window_end,
			"active_statuses": ACTIVE_APPOINTMENT_STATUSES,
		},
		as_dict=True,
	)
	for row in overall_rows:
		provider = row["appointment_provider"]
		metrics[provider]["overall_window_count"] = int(row["appointment_count"] or 0)
		metrics[provider]["last_assigned_at"] = row.get("last_assigned_at")

	if service_type:
		service_rows = frappe.db.sql(
			"""
			SELECT appointment_provider, COUNT(*) AS appointment_count
			FROM `tabService Appointment`
			WHERE appointment_provider IN %(providers)s
			  AND appointment_type = %(service_type)s
			  AND appointment_date BETWEEN %(window_start)s AND %(window_end)s
			  AND status IN %(active_statuses)s
			  AND docstatus != 2
			GROUP BY appointment_provider
			""",
			{
				"providers": provider_tuple,
				"service_type": service_type,
				"window_start": window_start,
				"window_end": window_end,
				"active_statuses": ACTIVE_APPOINTMENT_STATUSES,
			},
			as_dict=True,
		)
		for row in service_rows:
			metrics[row["appointment_provider"]]["service_window_count"] = int(row["appointment_count"] or 0)

	return metrics


def _same_gender(provider_gender: str | None, preferred_gender: str | None) -> bool:
	if not preferred_gender:
		return True
	if not provider_gender:
		return False
	return str(provider_gender).strip().lower() == str(preferred_gender).strip().lower()


def throw_no_provider_available(preferred_gender: str | None = None):
	if preferred_gender:
		frappe.throw(_("No available provider matches the preferred gender {0}.").format(preferred_gender))
	frappe.throw(_("No providers available for the selected time."))
