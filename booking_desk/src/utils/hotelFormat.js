/** Formatting helpers for the hotel pages. */

export function formatMoney(amount, currency) {
	const value = Number(amount || 0);
	try {
		return new Intl.NumberFormat(undefined, {
			style: "currency",
			currency: currency || "KES",
			maximumFractionDigits: 2,
		}).format(value);
	} catch {
		return `${currency || ""} ${value.toFixed(2)}`.trim();
	}
}

export function formatNight(value) {
	if (!value) return "";
	const date = new Date(`${String(value).slice(0, 10)}T00:00:00`);
	return date.toLocaleDateString(undefined, {
		weekday: "short",
		day: "numeric",
		month: "short",
	});
}

export function isoDate(date) {
	const pad = (n) => String(n).padStart(2, "0");
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function addDays(value, days) {
	const date = new Date(`${String(value).slice(0, 10)}T00:00:00`);
	date.setDate(date.getDate() + days);
	return isoDate(date);
}

export function nightsBetween(arrival, departure) {
	if (!arrival || !departure) return 0;
	const start = new Date(`${arrival}T00:00:00`);
	const end = new Date(`${departure}T00:00:00`);
	return Math.round((end - start) / 86400000);
}

/** "12:04" left of a hold that had `seconds` left at `fetchedAt` (ms), or null once it runs out. */
export function holdTimeLeft(seconds, fetchedAt, now = Date.now()) {
	if (seconds == null) return null;
	const left = Math.floor(seconds - (now - fetchedAt) / 1000);
	if (left <= 0) return null;
	return `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}`;
}
