import {
	fetchAvailableDatesApi,
	fetchAvailableSlotsApi,
	fetchCoupleAvailableSlotsApi,
} from "@/api/availability.api";

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

const toDateValue = (date) => {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");
	return `${year}-${month}-${day}`;
};

const getDefaultCoupleDateRange = () => {
	const start = new Date();
	const end = new Date(start);
	end.setDate(end.getDate() + 30);
	return { startDate: toDateValue(start), endDate: toDateValue(end) };
};

const normalizeCoupleLeg = (leg = {}, fallback = {}) => {
	const provider =
		leg.provider || leg.provider_id || fallback.provider || fallback.provider_id || "";
	const providerName =
		leg.providerName ||
		leg.provider_name ||
		fallback.providerName ||
		fallback.provider_name ||
		provider ||
		"Auto-assigned";
	const startTime =
		leg.startTime || leg.start_time || fallback.startTime || fallback.start_time || "";
	const endTime = leg.endTime || leg.end_time || fallback.endTime || fallback.end_time || "";

	return {
		provider,
		providerName,
		serviceUnit:
			leg.serviceUnit ||
			leg.service_unit ||
			fallback.serviceUnit ||
			fallback.service_unit ||
			null,
		serviceUnitName:
			leg.serviceUnitName ||
			leg.service_unit_name ||
			fallback.serviceUnitName ||
			fallback.service_unit_name ||
			null,
		startTime,
		endTime,
		duration: toNumber(
			leg.duration || leg.duration_minutes || fallback.duration || fallback.duration_minutes
		),
		bufferBefore: toNumber(
			leg.bufferBefore ||
				leg.buffer_before ||
				fallback.bufferBefore ||
				fallback.buffer_before
		),
		bufferAfter: toNumber(
			leg.bufferAfter || leg.buffer_after || fallback.bufferAfter || fallback.buffer_after
		),
		slotIds: Array.isArray(leg.slotIds)
			? leg.slotIds
			: Array.isArray(leg.slot_ids)
			? leg.slot_ids
			: [],
	};
};

const flattenCoupleRows = (response) => {
	const rows = Array.isArray(response) ? response : [];
	return rows.flatMap((row) => {
		if (!Array.isArray(row?.slots)) {
			return [row];
		}
		return row.slots.map((slot) => ({ ...slot, date: slot.date || row.date }));
	});
};

const normalizeCoupleSlot = (slot) => {
	const date = slot.date || slot.appointment_date || "";
	const sharedStartTime = slot.startTime || slot.start_time || "";
	const guest1 = normalizeCoupleLeg(slot.guest1 || slot.guest_1, {
		provider: slot.provider1 || slot.provider_1,
		provider_name: slot.providerName1 || slot.provider_name_1,
		service_unit: slot.serviceUnit1 || slot.service_unit_1,
		start_time: sharedStartTime,
		end_time: slot.endTime1 || slot.end_time_1,
		duration: slot.duration1 || slot.duration_1,
	});
	const guest2 = normalizeCoupleLeg(slot.guest2 || slot.guest_2, {
		provider: slot.provider2 || slot.provider_2,
		provider_name: slot.providerName2 || slot.provider_name_2,
		service_unit: slot.serviceUnit2 || slot.service_unit_2,
		start_time: sharedStartTime,
		end_time: slot.endTime2 || slot.end_time_2,
		duration: slot.duration2 || slot.duration_2,
	});
	const startTime = sharedStartTime || guest1.startTime || guest2.startTime;
	const candidateId =
		slot.candidateId ||
		slot.candidate_id ||
		slot.id ||
		`${date}:${startTime}:${guest1.provider}:${guest2.provider}`;

	return {
		id: candidateId,
		candidateId,
		date,
		startTime,
		endTime:
			slot.endTime ||
			slot.end_time ||
			[guest1.endTime, guest2.endTime].filter(Boolean).sort().at(-1) ||
			"",
		guest1,
		guest2,
		provider1: guest1.provider,
		provider2: guest2.provider,
		providerSummary: `Guest 1: ${guest1.providerName} · Guest 2: ${guest2.providerName}`,
		availability: guest1.provider && guest2.provider ? "available" : "unavailable",
		isCouple: true,
	};
};

const fetchNormalizedCoupleRows = async (params) => {
	const serviceType1 = normalizeServiceType(params.serviceType1);
	const serviceType2 = normalizeServiceType(params.serviceType2);
	if (!serviceType1 || !serviceType2) return [];

	const range = getDefaultCoupleDateRange();
	const response = await fetchCoupleAvailableSlotsApi({
		serviceType1,
		serviceType2,
		duration1: params.duration1,
		duration2: params.duration2,
		provider1: params.provider1,
		provider2: params.provider2,
		excludeAppointmentId1: params.excludeAppointmentId1,
		excludeAppointmentId2: params.excludeAppointmentId2,
		startDate: params.startDate || range.startDate,
		endDate: params.endDate || params.startDate || range.endDate,
	});

	return flattenCoupleRows(response)
		.map(normalizeCoupleSlot)
		.filter(
			(slot) => slot.date && slot.startTime && slot.guest1.provider && slot.guest2.provider
		);
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

export async function fetchNormalizedCoupleAvailableDates(params) {
	const slots = await fetchNormalizedCoupleRows(params);
	const dates = Array.from(new Set(slots.map((slot) => slot.date))).sort();
	return dates.map((date) => ({ date, label: formatDateLabel(date) }));
}

export async function fetchNormalizedCoupleAvailableSlots({ date, ...params }) {
	if (!date) return [];
	return fetchNormalizedCoupleRows({
		...params,
		startDate: date,
		endDate: date,
	});
}
