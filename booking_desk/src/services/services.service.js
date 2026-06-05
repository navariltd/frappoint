import {
	fetchCustomerRecentAppointments,
	fetchCustomers,
	fetchServiceTypeDetails,
	fetchServiceTypes,
	searchCustomers,
} from "@/api/services.api";

const toAmount = (value) => {
	const numeric = Number(value);
	return Number.isFinite(numeric) ? numeric : 0;
};

const toCategory = (row) => row.item_group || "General";

const sanitizeDescription = (row) => {
	const source = row.short_description || "No description available";
	return String(source).trim();
};

const normalizePackage = (row) => ({
	id: row.price_name || `${row.duration || 0}-${toAmount(row.amount)}`,
	name: row.price_name || "Default Package",
	amount: toAmount(row.amount),
	duration: Number(row.duration) || null,
	currency: row.currency || "KES",
	pricingModel: row.pricing_model || "",
	guestCount: Number(row.guest_count) || null,
});

const normalizeProvider = (row) => ({
	id: row.name || row.provider || "",
	name: row.provider_name || row.providerName || row.name || row.provider || "",
	gender: row.gender || "",
	designation: row.designation || "",
});

const findPriceForDuration = (prices, targetDuration) => {
	if (!prices || !prices.length) {
		return null;
	}

	// Exact match first
	const exact = prices.find((p) => p.duration === targetDuration);
	if (exact) {
		return exact;
	}

	// Closest match
	return prices.reduce((closest, current) => {
		if (!closest) return current;
		const closestDiff = Math.abs((closest.duration || 0) - targetDuration);
		const currentDiff = Math.abs((current.duration || 0) - targetDuration);
		return currentDiff < closestDiff ? current : closest;
	});
};

export async function fetchNormalizedServices() {
	const serviceRows = await fetchServiceTypes();

	return serviceRows.map((row) => {
		const serviceName = row.name;
		const defaultDuration = Number(row.default_duration_in_minutes) || 0;
		const displayPrice = row.price ? normalizePackage(row.price) : null;

		return {
			id: serviceName,
			name: row.appointment_type || serviceName,
			description: sanitizeDescription(row),
			duration: defaultDuration,
			price: displayPrice?.amount || 0,
			currency: displayPrice?.currency || "KES",
			category: toCategory(row),
			isActive: true,
			defaultPackageId: displayPrice?.id || "",
			availablePrices: displayPrice ? [displayPrice] : [],
			hasMultiplePrices: false,
		};
	});
}

export async function fetchServicePackages(serviceId, preferredDuration = 0) {
	const details = await fetchServiceTypeDetails(serviceId);
	const prices = Array.isArray(details?.prices) ? details.prices : [];
	const packages = prices.map(normalizePackage);
	const defaultPackage =
		findPriceForDuration(packages, Number(preferredDuration) || 0) || packages[0] || null;

	return {
		serviceId,
		packages,
		defaultPackage,
		providers: Array.isArray(details?.providers)
			? details.providers.map(normalizeProvider).filter((provider) => provider.id)
			: [],
		paymentGateways: Array.isArray(details?.payment_gateways) ? details.payment_gateways : [],
		minGuests: Number(details?.min_guests) || null,
		maxGuests: Number(details?.max_guests) || null,
	};
}

export function buildServiceCategories(services) {
	const categorySet = new Set(services.map((service) => service.category).filter(Boolean));
	return ["All", ...Array.from(categorySet).sort((a, b) => a.localeCompare(b))];
}

export async function fetchNormalizedCustomers(pageLength = 100) {
	const customers = await fetchCustomers(pageLength);
	return customers.map((row) => ({
		id: row.name,
		name: row.customer_name || row.name,
	}));
}

export async function searchNormalizedCustomers(query = "", pageLength = 50) {
	const customers = await searchCustomers(query, pageLength);
	return customers.map((row) => ({
		id: row.name,
		name: row.customer_name || row.name,
	}));
}

export async function fetchCustomerSummary(customerId, customerName = "") {
	if (!customerId) {
		return {
			id: "",
			name: "No customer selected",
			phone: "-",
			email: "-",
			recentBookingsCount: 0,
			outstandingBalance: 0,
			isVip: false,
		};
	}

	const appointments = await fetchCustomerRecentAppointments(customerId);
	const latest = appointments[0] || {};

	const outstandingBalance = appointments.reduce(
		(sum, row) => sum + toAmount(row.outstanding_amount),
		0
	);
	const completedVisits = appointments.filter(
		(row) => String(row.status || "").toLowerCase() === "completed"
	).length;

	return {
		id: customerId,
		name: latest.full_name || customerName || customerId,
		phone: latest.mobile_no || "-",
		email: latest.email || "-",
		recentBookingsCount: appointments.length,
		outstandingBalance,
		isVip: completedVisits >= 10,
	};
}
