export const BOOKING_WORKFLOW_STORAGE_KEY = "booking-desk.workflow.v1";

export function createEmptyDraftBooking() {
	return {
		id: "",
		name: "",
		status: "Draft",
		customerId: "",
		fullName: "",
		email: "",
		mobileNo: "",
		bookedBy: "",
		currency: "KES",
		subtotal: 0,
		grandTotal: 0,
		totalGuests: 0,
		items: [],
		appointments: [],
		isCouple: false,
		coupleServiceKeys: [],
		cartItemsSnapshot: [],
		customerSnapshot: null,
	};
}
