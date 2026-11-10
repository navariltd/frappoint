"""Feature-flag guards for the hospitality module.

Every hospitality entry point goes through one of these, so turning `enable_hospitality` off
switches the whole module off:

- `require_hospitality` for whitelisted APIs and commands: raises a clear error.
- `hospitality_job` for scheduler jobs and doc-event hooks: returns quietly.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

import frappe
from frappe import _

from frappoint.vuna_hospitality.doctype.hospitality_settings.hospitality_settings import (
	is_hospitality_enabled,
)

__all__ = ["HospitalityDisabledError", "hospitality_job", "is_hospitality_enabled", "require_hospitality"]


GUARD_ATTRIBUTE = "_hospitality_guarded"


class HospitalityDisabledError(frappe.ValidationError):
	pass


def assert_hospitality_enabled() -> None:
	if not is_hospitality_enabled():
		raise HospitalityDisabledError(
			_("Hospitality is not enabled on this site. Enable it in Hospitality Settings.")
		)


def require_hospitality(fn: Callable) -> Callable:
	"""Refuse to run `fn` while hospitality is disabled. Use under `@frappe.whitelist()`."""

	@wraps(fn)
	def wrapper(*args: Any, **kwargs: Any):
		assert_hospitality_enabled()
		return fn(*args, **kwargs)

	setattr(wrapper, GUARD_ATTRIBUTE, True)
	return wrapper


def hospitality_job(fn: Callable) -> Callable:
	"""Skip `fn` (returning None) while hospitality is disabled. Use for jobs and doc events."""

	@wraps(fn)
	def wrapper(*args: Any, **kwargs: Any):
		if not is_hospitality_enabled():
			return None
		return fn(*args, **kwargs)

	setattr(wrapper, GUARD_ATTRIBUTE, True)
	return wrapper
