"""Shared test helpers for hospitality features.

- `hospitality_enabled(state)`: run a block with the module switched on or off.
- `run_concurrently(*fns)`: run functions at the same time on separate database connections,
  to prove locking (for example, that two bookings can't take the last room).
"""

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import frappe

from frappoint.vuna_hospitality.constants import SETTINGS_DOCTYPE


@contextmanager
def hospitality_enabled(state: bool = True) -> Iterator[None]:
	"""Set `enable_hospitality` for the duration of the block, then restore it."""
	previous = frappe.db.get_single_value(SETTINGS_DOCTYPE, "enable_hospitality")
	_set_flag(int(state))
	try:
		yield
	finally:
		_set_flag(previous or 0)


def _set_flag(value: int) -> None:
	# Write directly (no on_update side effects) and drop the per-request value cache that
	# `is_hospitality_enabled()` reads from.
	frappe.db.set_single_value(SETTINGS_DOCTYPE, "enable_hospitality", value)
	frappe.db.value_cache.pop(SETTINGS_DOCTYPE, None)
	frappe.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)


@dataclass
class ConcurrentResult:
	value: Any = None
	error: BaseException | None = None

	@property
	def ok(self) -> bool:
		return self.error is None


def run_concurrently(
	*fns: Callable[[], Any],
	user: str = "Administrator",
	start_timeout: float = 10,
	commit: bool = True,
) -> list[ConcurrentResult]:
	"""Run each function in its own thread with its own Frappe site connection.

	All threads connect first, then start together, so their transactions genuinely overlap.
	Each thread commits on success (unless `commit=False`) and rolls back on error. Errors are
	returned in the result, not raised, so a test can assert exactly one winner.

	Data the functions need must be committed beforehand, because the other connections can't see
	the test's uncommitted transaction. Clean it up afterwards.
	"""
	site = frappe.local.site
	sites_path = frappe.local.sites_path
	results = [ConcurrentResult() for _ in fns]
	ready = threading.Barrier(len(fns))

	def worker(index: int, fn: Callable[[], Any]) -> None:
		frappe.init(site=site, sites_path=sites_path)
		try:
			frappe.connect()
			frappe.set_user(user)
			ready.wait(timeout=start_timeout)
			results[index].value = fn()
			if commit:
				frappe.db.commit()
			else:
				frappe.db.rollback()
		except BaseException as error:
			results[index].error = error
			if getattr(frappe.local, "db", None):
				frappe.db.rollback()
		finally:
			frappe.destroy()

	threads = [threading.Thread(target=worker, args=(i, fn), daemon=True) for i, fn in enumerate(fns)]
	for thread in threads:
		thread.start()
	for thread in threads:
		thread.join(timeout=start_timeout + 60)
	return results
