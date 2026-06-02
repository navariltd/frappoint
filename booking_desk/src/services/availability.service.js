import { fetchAvailableDatesApi, fetchAvailableSlotsApi } from "@/api/availability.api";

const dateFormatter = new Intl.DateTimeFormat("en-US", {
	weekday: "short",
	month: "short",
	day: "numeric",
});

const toNumber = (value, fallback = 0) => {
	const parsed = Number(value);
	return Number.isFinite(parsed) ? parsed : fallback;
};

const normalizeServiceType = (value) => {
	if (value === null || value === undefined) return "";
	const normalized = String(value).trim();
	if (!normalized) return "";
	const lower = normalized.toLowerCase();
	if (lower === "null" || lower === "undefined" || lower === "[object object]") return "";
	return normalized;
};

const formatDateLabel = (dateValue) => {
	if (!dateValue) {
		return "";
	}
	const parsed = new Date(`${dateValue}T00:00:00`);
	if (Number.isNaN(parsed.getTime())) {
		return String(dateValue);
	}
	return dateFormatter.format(parsed);
};

const toProviderSummary = (providers = []) => {
	if (!providers.length) {
		return "No provider";
	}
	if (providers.length === 1) {
		return providers[0].providerName;
	}
	return `${providers.length} providers`;
};

const normalizeProviders = (providers = []) => {
	return providers.map((provider) => ({
		provider: provider.provider || "",
		providerName: provider.provider_name || "Any available",
		serviceUnit: provider.service_unit || null,
		serviceUnitName: provider.service_unit_name || null,
		slotIds: Array.isArray(provider.slot_ids) ? provider.slot_ids : [],
	}));
};

const normalizeSlot = (slot, date) => {
	const providers = normalizeProviders(slot.providers || []);
	const availability =
		providers.length > 1 ? "partial" : providers.length ? "available" : "unavailable";
	return {
		id: `${date}:${slot.start_time}-${slot.end_time}`,
		date,
		startTime: slot.start_time,
		endTime: slot.end_time,
		duration: toNumber(slot.duration),
		availability,
		providers,
		providerSummary: toProviderSummary(providers),
	};
};

export async function fetchNormalizedAvailableDates({ serviceType, duration, provider, gender }) {
	const normalizedServiceType = normalizeServiceType(serviceType);
	if (!normalizedServiceType) return [];

	const response = await fetchAvailableDatesApi({
		serviceType: normalizedServiceType,
		duration,
		provider,
		gender,
	});
	const rows = Array.isArray(response) ? response : [];
	return rows.map((date) => ({
		date,
		label: formatDateLabel(date),
	}));
}

export async function fetchNormalizedAvailableSlots({
	serviceType,
	duration,
	provider,
	date,
	gender,
	useCounterEngine,
}) {
	const normalizedServiceType = normalizeServiceType(serviceType);
	if (!normalizedServiceType) return [];

	const response = await fetchAvailableSlotsApi({
		serviceType: normalizedServiceType,
		duration,
		provider,
		date,
		gender,
		useCounterEngine,
	});
	const dateGroups = Array.isArray(response) ? response : [];
	const targetGroup = dateGroups.find((group) => String(group.date) === String(date));
	const rawSlots = targetGroup?.slots || [];
	return rawSlots.map((slot) => normalizeSlot(slot, date));
}
