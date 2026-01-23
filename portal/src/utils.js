export function formatCurrency(amount, currency) {
	return Intl.NumberFormat("en-US", { style: "currency", currency: currency }).format(amount);
}

export function buildDate(date, time) {
	if (!date || !time) return null;

	const [h, m, s = "00"] = time.split(":");
	const d = new Date(
		Number(date.slice(0, 4)),
		Number(date.slice(5, 7)) - 1,
		Number(date.slice(8, 10)),
		Number(h),
		Number(m),
		Number(s)
	);

	return isNaN(d.getTime()) ? null : d;
}
