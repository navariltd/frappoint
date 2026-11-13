/**
 * A short-lived, in-memory cache of availability searches, kept for the browser tab.
 *
 * Availability changes whenever anyone books, so results are only shown from the cache, never
 * trusted: a result younger than FRESH_MS is shown as is; an older one is shown at once and
 * refreshed in the background; one older than MAX_AGE_MS is dropped. Holding a room re-checks
 * availability on the server anyway. Booking a room clears the cache, since every result that
 * included it is now out of date.
 */

const FRESH_MS = 60 * 1000;
const MAX_AGE_MS = 10 * 60 * 1000;
const MAX_ENTRIES = 30;

const entries = new Map();

/** One key per search: the same property, dates and guests give the same key. */
export function availabilityKey(params) {
	return JSON.stringify([
		params.property,
		params.arrival,
		params.departure,
		Number(params.adults) || 0,
		Number(params.children) || 0,
		params.childAges || [],
	]);
}

/** {results, fresh} for a cached search, or null. */
export function readAvailability(key) {
	const entry = entries.get(key);
	if (!entry) return null;
	const age = Date.now() - entry.at;
	if (age > MAX_AGE_MS) {
		entries.delete(key);
		return null;
	}
	return { results: entry.results, fresh: age < FRESH_MS };
}

export function writeAvailability(key, results) {
	entries.delete(key); // re-insert, so the oldest entries are first
	entries.set(key, { results, at: Date.now() });
	while (entries.size > MAX_ENTRIES) entries.delete(entries.keys().next().value);
}

export function clearAvailability() {
	entries.clear();
}
