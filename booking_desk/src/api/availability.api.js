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

export async function fetchAvailableDatesApi({
	serviceType,
	duration,
	provider,
	gender,
	daysAhead = 30,
}) {
	console.log("DEBUG: fetchAvailableDatesApi called with GENDER:", gender);
	const params = { service_type: serviceType, duration, days_ahead: daysAhead };
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
	daysAhead = 30,
}) {
	const params = { service_type: serviceType, duration, date, days_ahead: daysAhead };
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
