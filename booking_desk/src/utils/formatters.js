import { branding } from "@/branding";

/**
 * Formats a time string (e.g., "16:00:00", "16:00", "09:30:00", "4:00 PM") into
 * 24-hour ("16:00") or 12-hour ("4:00 PM") based on use24Hour or branding.use24HourClockSystem.
 *
 * @param {string|null|undefined} value
 * @param {boolean} [use24Hour=branding.use24HourClockSystem]
 * @returns {string} Formatted time or empty string
 */
export function formatTime(value, use24Hour = branding.use24HourClockSystem) {
	if (!value) return "";
	const raw = String(value).trim();

	const ampmMatch = raw.match(/^(\d{1,2}):(\d{2})(?::\d{2})?\s*(am|pm)$/i);
	let hours, minutes;
	if (ampmMatch) {
		const hour12 = parseInt(ampmMatch[1], 10);
		minutes = ampmMatch[2];
		const isPm = ampmMatch[3].toLowerCase() === "pm";
		hours = (hour12 % 12) + (isPm ? 12 : 0);
	} else {
		const match = raw.match(/^(\d{1,2}):(\d{2})(?::\d{2})?/);
		if (!match) return raw;
		hours = parseInt(match[1], 10);
		minutes = match[2];
	}

	if (use24Hour) {
		return `${String(hours).padStart(2, "0")}:${minutes}`;
	} else {
		const ampm = hours >= 12 ? "PM" : "AM";
		const displayHour = hours % 12 || 12;
		return `${displayHour}:${minutes} ${ampm}`;
	}
}

/**
 * Formats a date string (yyyy-mm-dd) into dd-mm-yyyy.
 * @param {string|null|undefined} value
 * @returns {string} Formatted date or empty string
 */
export function formatDate(value) {
	if (!value) return "";
	// Expecting format YYYY-MM-DD
	const parts = String(value).split("-");
	if (parts.length !== 3) return value;
	const [year, month, day] = parts;
	return `${day}-${month}-${year}`;
}
