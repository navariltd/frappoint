export function formatCurrency(amount, currency) {
	return Intl.NumberFormat("en-US", { style: "currency", currency: currency }).format(amount);
}
