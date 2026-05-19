export const BOOKING_VIEWS = {
	BOOKINGS: "bookings",
	APPOINTMENTS: "appointments",
	CALENDAR: "calendar",
};

export const BOOKING_STATUSES = [
	"Draft",
	"Confirmed",
	"Checked In",
	"In Progress",
	"Completed",
	"Cancelled",
];

export const PAYMENT_STATUSES = ["Unpaid", "Partly Paid", "Paid"];

export function createEmptyBookingFilters() {
	return {
		searchText: "",
		customerQuery: "",
		statuses: [],
		paymentStatuses: [],
		fromDate: "",
		toDate: "",
	};
}

export function createEmptyBookingsState() {
	return {
		bookings: [],
		page: 1,
		pageSize: 20,
		hasMore: false,
		isLoading: false,
		error: "",
		selectedView: BOOKING_VIEWS.BOOKINGS,
		filters: createEmptyBookingFilters(),
	};
}
