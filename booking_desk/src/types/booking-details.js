export function createEmptyBookingDetails() {
	return {
		id: "",
		bookingId: "",
		status: "Draft",
		paymentStatus: "Unpaid",
		customer: "",
		customerName: "",
		email: "",
		mobileNo: "",
		currency: "KES",
		bookingDate: "",
		appointmentCount: 0,
		totalGuests: 0,
		subtotal: 0,
		grandTotal: 0,
		paidAmount: 0,
		outstandingAmount: 0,
		items: [],
		appointments: [],
		alerts: [],
	};
}
