/**
 * Formats a time string (e.g., "16:00:00", "9:30:00", "16:00") into "HH:mm" by removing seconds.
 *
 * @param {string|null|undefined} value
 * @returns {string} Formatted time as "HH:mm" or empty string
 */
export function formatTime(value) {
	if (!value) return "";
	const raw = String(value).trim();
	const match = raw.match(/^(\d{1,2}):(\d{2})(?::\d{2})?/);
	if (match) {
		return `${match[1].padStart(2, "0")}:${match[2]}`;
	}
	return raw;
}
