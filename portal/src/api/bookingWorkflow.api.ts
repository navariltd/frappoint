import { createResource } from "frappe-ui";

const CREATE_DRAFT_BOOKING_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.create_draft_service_booking";
const GET_DRAFT_BOOKING_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.get_draft_service_booking";
const UPSERT_DRAFT_APPOINTMENT_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.upsert_draft_service_appointment";
const AVAILABLE_DATES_ENDPOINT = "frappoint.frappoint.api.slot_availability.get_available_dates";
const AVAILABLE_SLOTS_ENDPOINT =
	"frappoint.frappoint.api.slot_availability.get_available_time_slots";
const CHECK_SLOT_AVAILABILITY_ENDPOINT =
	"frappoint.frappoint.api.slot_availability.check_slot_availability";
const GET_LOGGED_IN_CUSTOMER_ENDPOINT =
	"frappoint.frappoint.api.user.get_logged_in_customer";

const createDraftBookingResource = createResource({
	url: CREATE_DRAFT_BOOKING_ENDPOINT,
	auto: false,
});

const getDraftBookingResource = createResource({
	url: GET_DRAFT_BOOKING_ENDPOINT,
	auto: false,
});

const upsertDraftAppointmentResource = createResource({
	url: UPSERT_DRAFT_APPOINTMENT_ENDPOINT,
	auto: false,
});

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

const loggedInCustomerResource = createResource({
	url: GET_LOGGED_IN_CUSTOMER_ENDPOINT,
	method: "GET",
	auto: false,
});

const unwrapPayload = <T>(payload: any): T => {
	if (Array.isArray(payload)) {
		return payload as T;
	}
	if (Array.isArray(payload?.message)) {
		return payload.message as T;
	}
	return (payload?.message ?? payload ?? null) as T;
};

export async function createDraftServiceBookingApi({
	customer,
	items,
}: {
	customer: Record<string, any>;
	items: Array<Record<string, any>>;
}) {
	const response = await createDraftBookingResource.fetch({
		customer: JSON.stringify(customer || {}),
		items: JSON.stringify(items || []),
	});
	return unwrapPayload<Record<string, any>>(response ?? createDraftBookingResource.data);
}

export async function getDraftServiceBookingApi(bookingId: string) {
	const response = await getDraftBookingResource.fetch({ booking_id: bookingId });
	return unwrapPayload<Record<string, any>>(response ?? getDraftBookingResource.data);
}

export async function upsertDraftServiceAppointmentApi({
	bookingId,
	appointmentId,
	assignment,
}: {
	bookingId: string;
	appointmentId?: string;
	assignment: Record<string, any>;
}) {
	const response = await upsertDraftAppointmentResource.fetch({
		booking_id: bookingId,
		appointment_id: appointmentId || undefined,
		assignment: JSON.stringify(assignment || {}),
	});
	return unwrapPayload<Record<string, any>>(response ?? upsertDraftAppointmentResource.data);
}

export async function fetchAvailableDatesApi({
	serviceType,
	duration,
	provider,
	daysAhead = 30,
}: {
	serviceType: string;
	duration: number;
	provider?: string;
	daysAhead?: number;
}) {
	const params: Record<string, any> = {
		service_type: serviceType,
		duration,
		days_ahead: daysAhead,
	};
	if (provider) params.provider = provider;
	const response = await availableDatesResource.fetch(params);
	return unwrapPayload<string[]>(response ?? availableDatesResource.data);
}

export async function fetchAvailableSlotsApi({
	serviceType,
	duration,
	provider,
	date,
	daysAhead = 30,
}: {
	serviceType: string;
	duration: number;
	provider?: string;
	date: string;
	daysAhead?: number;
}) {
	const params: Record<string, any> = {
		service_type: serviceType,
		duration,
		date,
		days_ahead: daysAhead,
	};
	if (provider) params.provider = provider;
	const response = await availableSlotsResource.fetch(params);
	return unwrapPayload<Array<Record<string, any>>>(response ?? availableSlotsResource.data);
}

export async function checkSlotAvailabilityApi(slotIds: string[]) {
	const response = await checkSlotAvailabilityResource.fetch({
		slot_ids: slotIds,
	});
	return unwrapPayload<Record<string, any>>(response ?? checkSlotAvailabilityResource.data);
}

export async function getLoggedInCustomerApi() {
	const response = await loggedInCustomerResource.fetch();
	return unwrapPayload<Record<string, any>>(response ?? loggedInCustomerResource.data);
}
