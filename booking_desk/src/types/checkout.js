export function createEmptyCheckoutSummary() {
	return {
		booking: {
			name: "",
			status: "Draft",
			customer: "",
			fullName: "",
			email: "",
			mobileNo: "",
			currency: "KES",
			subtotal: 0,
			grandTotal: 0,
			outstandingAmount: 0,
			items: [],
			appointments: [],
		},
		payment: {
			referenceDoctype: "Service Booking",
			referenceDocname: "",
			currency: "KES",
			totalAmount: 0,
			paidAmount: 0,
			outstandingAmount: 0,
			minimumDue: 0,
			depositPercent: 100,
			canConfirmWithoutPayment: false,
		},
	};
}
