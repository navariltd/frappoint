import { createResource } from "frappe-ui";

const CREATE_DRAFT_BOOKING_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.create_draft_service_booking";
const GET_DRAFT_BOOKING_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.get_draft_service_booking";

const createDraftBookingResource = createResource({
	url: CREATE_DRAFT_BOOKING_ENDPOINT,
	auto: false,
});

const getDraftBookingResource = createResource({
	url: GET_DRAFT_BOOKING_ENDPOINT,
	auto: false,
});

const unwrapPayload = (payload) => payload?.message ?? payload ?? null;

export async function createDraftServiceBookingApi({
	customer,
	items,
	bookedBy,
	isCouple,
	coupleAssignment,
}) {
	const params = {
		customer: JSON.stringify(customer || {}),
		items: JSON.stringify(items || []),
		booked_by: bookedBy || "",
	};
	if (isCouple) params.is_couple = 1;
	if (coupleAssignment) {
		params.couple_assignment = JSON.stringify(coupleAssignment);
	}
	const response = await createDraftBookingResource.fetch(params);
	return unwrapPayload(response ?? createDraftBookingResource.data);
}

export async function getDraftServiceBookingApi(bookingId) {
	const response = await getDraftBookingResource.fetch({ booking_id: bookingId });
	return unwrapPayload(response ?? getDraftBookingResource.data);
}
