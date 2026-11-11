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
	frontDeskToday: `${HOSPITALITY_API}.front_desk.get_front_desk_today`,
	stay: `${HOSPITALITY_API}.front_desk.get_stay`,
	assignableRooms: `${HOSPITALITY_API}.front_desk.get_assignable_rooms`,
	moveReasons: `${HOSPITALITY_API}.front_desk.get_move_reasons`,
	assignRoom: `${HOSPITALITY_API}.front_desk.assign_room`,
	unassignRoom: `${HOSPITALITY_API}.front_desk.unassign_room`,
	setRoomLock: `${HOSPITALITY_API}.front_desk.set_room_lock`,
	moveRoom: `${HOSPITALITY_API}.front_desk.move_room`,
	checkIn: `${HOSPITALITY_API}.front_desk.check_in`,
	checkOut: `${HOSPITALITY_API}.front_desk.check_out`,
	addStayGuest: `${HOSPITALITY_API}.front_desk.add_stay_guest`,
	removeStayGuest: `${HOSPITALITY_API}.front_desk.remove_stay_guest`,
	setPrimaryGuest: `${HOSPITALITY_API}.front_desk.set_primary_guest`,
	registerGuest: `${HOSPITALITY_API}.front_desk.register_guest`,
	checkInGuest: `${HOSPITALITY_API}.front_desk.check_in_guest`,
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

// Front desk (F6)
export const fetchFrontDeskTodayApi = (property) =>
	request(HOTEL_ENDPOINTS.frontDeskToday, { property });
export const fetchStayApi = (stay) => request(HOTEL_ENDPOINTS.stay, { stay });
export const fetchAssignableRoomsApi = (stay) =>
	request(HOTEL_ENDPOINTS.assignableRooms, { stay });
export const fetchMoveReasonsApi = () => request(HOTEL_ENDPOINTS.moveReasons);
export const assignRoomApi = (stay, room, lock = false) =>
	request(HOTEL_ENDPOINTS.assignRoom, { stay, room, lock: lock ? 1 : 0 });
export const unassignRoomApi = (stay, reason) =>
	request(HOTEL_ENDPOINTS.unassignRoom, { stay, reason });
export const setRoomLockApi = (stay, locked, reason) =>
	request(HOTEL_ENDPOINTS.setRoomLock, { stay, locked: locked ? 1 : 0, reason });
export const moveRoomApi = (stay, room, moveReason) =>
	request(HOTEL_ENDPOINTS.moveRoom, { stay, room, move_reason: moveReason });
export const checkInApi = (stay, room) =>
	request(HOTEL_ENDPOINTS.checkIn, { stay, room: room || null });
export const checkOutApi = (stay) => request(HOTEL_ENDPOINTS.checkOut, { stay });
export const addStayGuestApi = (stay, guestProfile, ageCategory = "Adult") =>
	request(HOTEL_ENDPOINTS.addStayGuest, {
		stay,
		guest_profile: guestProfile,
		age_category: ageCategory,
	});
export const removeStayGuestApi = (stayGuest, reason) =>
	request(HOTEL_ENDPOINTS.removeStayGuest, { stay_guest: stayGuest, reason });
export const setPrimaryGuestApi = (stayGuest) =>
	request(HOTEL_ENDPOINTS.setPrimaryGuest, { stay_guest: stayGuest });
export const registerGuestApi = (stayGuest) =>
	request(HOTEL_ENDPOINTS.registerGuest, { stay_guest: stayGuest });
export const checkInGuestApi = (stayGuest) =>
	request(HOTEL_ENDPOINTS.checkInGuest, { stay_guest: stayGuest });
