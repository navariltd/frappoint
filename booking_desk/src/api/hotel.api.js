import { createResource } from "frappe-ui";

const HOSPITALITY_API = "frappoint.vuna_hospitality.api";

export const HOTEL_ENDPOINTS = {
	sessionContext: `${HOSPITALITY_API}.session.get_session_context`,
	deskContext: `${HOSPITALITY_API}.reservations.get_booking_desk_context`,
	searchAvailability: `${HOSPITALITY_API}.quote.search_availability`,
	searchGuests: `${HOSPITALITY_API}.guests.search_guests`,
	createGuest: `${HOSPITALITY_API}.guests.create_guest`,
	holdStays: `${HOSPITALITY_API}.reservations.hold_stays`,
	confirmStay: `${HOSPITALITY_API}.reservations.confirm_stay`,
	confirmBooking: `${HOSPITALITY_API}.reservations.confirm_booking`,
	cancelStay: `${HOSPITALITY_API}.reservations.cancel_stay`,
	cancelBooking: `${HOSPITALITY_API}.reservations.cancel_booking`,
	getBooking: `${HOSPITALITY_API}.reservations.get_booking`,
	recentBookings: `${HOSPITALITY_API}.reservations.get_recent_bookings`,
};

const unwrapPayload = (payload) => payload?.message ?? payload ?? null;

async function request(url, params = {}) {
	const resource = createResource({ url, auto: false });
	const response = await resource.fetch(params);
	return unwrapPayload(response ?? resource.data);
}

/** The server's message for a failed call, without the traceback. */
export function hotelErrorMessage(error) {
	const messages = error?.messages?.filter(Boolean);
	if (messages?.length) return messages.join(" ");
	return error?.message || "Something went wrong. Please try again.";
}

export const fetchSessionContextApi = () => request(HOTEL_ENDPOINTS.sessionContext);
export const fetchDeskContextApi = () => request(HOTEL_ENDPOINTS.deskContext);

export const searchAvailabilityApi = ({ property, arrival, departure, adults, children }) =>
	request(HOTEL_ENDPOINTS.searchAvailability, {
		property,
		arrival,
		departure,
		adults,
		children,
	});

export const searchGuestsApi = (text) => request(HOTEL_ENDPOINTS.searchGuests, { text });

export const createGuestApi = (guest) => request(HOTEL_ENDPOINTS.createGuest, guest);

export const holdStaysApi = ({ property, stays, booking, bookingDetails }) =>
	request(HOTEL_ENDPOINTS.holdStays, {
		property,
		stays,
		booking: booking || null,
		booking_details: bookingDetails || {},
	});

export const confirmStayApi = (stay) => request(HOTEL_ENDPOINTS.confirmStay, { stay });
export const confirmBookingApi = (booking) => request(HOTEL_ENDPOINTS.confirmBooking, { booking });
export const cancelStayApi = (stay, reason) =>
	request(HOTEL_ENDPOINTS.cancelStay, { stay, reason });
export const cancelBookingApi = (booking, reason) =>
	request(HOTEL_ENDPOINTS.cancelBooking, { booking, reason });
export const fetchBookingApi = (booking) => request(HOTEL_ENDPOINTS.getBooking, { booking });
export const fetchRecentBookingsApi = (property) =>
	request(HOTEL_ENDPOINTS.recentBookings, { property });
