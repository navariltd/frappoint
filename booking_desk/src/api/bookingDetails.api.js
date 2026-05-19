import { createResource } from "frappe-ui";

const GET_BOOKING_DETAILS_ENDPOINT = "frappoint.frappoint.api.booking_desk.get_booking_details";

const bookingDetailsResource = createResource({
	url: GET_BOOKING_DETAILS_ENDPOINT,
	auto: false,
});

const unwrapPayload = (payload) => payload?.message ?? payload ?? null;

export async function fetchBookingDetailsApi(bookingId) {
	const response = await bookingDetailsResource.fetch({ booking_id: bookingId });
	return unwrapPayload(response ?? bookingDetailsResource.data);
}
