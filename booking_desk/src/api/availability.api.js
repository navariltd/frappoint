import { createResource } from "frappe-ui";

const AVAILABLE_DATES_ENDPOINT = "frappoint.frappoint.api.slot_availability.get_available_dates";
const AVAILABLE_SLOTS_ENDPOINT =
	"frappoint.frappoint.api.slot_availability.get_available_time_slots";
const CHECK_SLOT_AVAILABILITY_ENDPOINT =
	"frappoint.frappoint.api.slot_availability.check_slot_availability";

const availableDatesResource = createResource({
	url: AVAILABLE_DATES_ENDPOINT,
	method: "GET",
	auto: false,
});

const availableSlotsResource = createResource({
	url: AVAILABLE_SLOTS_ENDPOINT,
	method: "GET",
	auto: false,
});

const checkSlotAvailabilityResource = createResource({
	url: CHECK_SLOT_AVAILABILITY_ENDPOINT,
	auto: false,
});

const unwrapPayload = (payload) => {
	if (Array.isArray(payload)) {
		return payload;
	}
	if (Array.isArray(payload?.message)) {
		return payload.message;
	}
	return payload?.message ?? payload ?? null;
};

const getValidDaysAhead = (value) => {
	if (value === undefined || value === null || value === "") {
		return null;
	}

	if (typeof value === "string") {
		const normalized = value.trim().toLowerCase();
		if (!normalized || normalized === "undefined" || normalized === "null") {
			return null;
		}
	}

	const parsed = Number(value);
	if (!Number.isFinite(parsed) || parsed <= 0) {
		return null;
	}

	return Math.floor(parsed);
};

export async function fetchAvailableDatesApi({
	serviceType,
	duration,
	provider,
	gender,
	daysAhead,
}) {
	const params = { service_type: serviceType, duration };
	const sanitizedDaysAhead = getValidDaysAhead(daysAhead);
	if (sanitizedDaysAhead) params.days_ahead = sanitizedDaysAhead;
	if (provider) params.provider = provider;
	if (gender) params.gender = gender;
	const response = await availableDatesResource.fetch(params);
	return unwrapPayload(response ?? availableDatesResource.data);
}

export async function fetchAvailableSlotsApi({
	serviceType,
	duration,
	provider,
	date,
	gender,
	daysAhead,
}) {
	const params = { service_type: serviceType, duration, date };
	const sanitizedDaysAhead = getValidDaysAhead(daysAhead);
	if (sanitizedDaysAhead) params.days_ahead = sanitizedDaysAhead;
	if (provider) params.provider = provider;
	if (gender) params.gender = gender;
	const response = await availableSlotsResource.fetch(params);
	return unwrapPayload(response ?? availableSlotsResource.data);
}

export async function checkSlotAvailabilityApi(slotIds = []) {
	const response = await checkSlotAvailabilityResource.fetch({
		slot_ids: slotIds,
	});
	return unwrapPayload(response ?? checkSlotAvailabilityResource.data);
}

export {
	AVAILABLE_DATES_ENDPOINT,
	AVAILABLE_SLOTS_ENDPOINT,
	CHECK_SLOT_AVAILABILITY_ENDPOINT,
	availableDatesResource,
	availableSlotsResource,
	checkSlotAvailabilityResource,
};
