import { defineStore } from "pinia";
import { createEmptyBookingDetails } from "@/types/booking-details";
import { fetchBookingDetails } from "@/services/bookingDetails.service";

export const useBookingDetailsStore = defineStore("bookingDetails", {
	state: () => ({
		booking: createEmptyBookingDetails(),
		isLoading: false,
		error: "",
	}),
	getters: {
		hasBooking(state) {
			return Boolean(state.booking?.bookingId);
		},
		hasAppointments(state) {
			return (state.booking?.appointments || []).length > 0;
		},
		financialSummary(state) {
			return {
				currency: state.booking.currency || "KES",
				subtotal: Number(state.booking.subtotal || 0),
				grandTotal: Number(state.booking.grandTotal || 0),
				paidAmount: Number(state.booking.paidAmount || 0),
				outstandingAmount: Number(state.booking.outstandingAmount || 0),
				depositAmount: Math.max(
					0,
					Number(state.booking.grandTotal || 0) -
						Number(state.booking.outstandingAmount || 0)
				),
			};
		},
		summaryMetrics(state) {
			return {
				appointmentCount: Number(state.booking.appointmentCount || 0),
				totalGuests: Number(state.booking.totalGuests || 0),
				status: state.booking.status || "Draft",
				paymentStatus: state.booking.paymentStatus || "Unpaid",
			};
		},
	},
	actions: {
		async fetchBooking(bookingId) {
			if (!bookingId) {
				this.error = "Booking ID is required.";
				return;
			}
			this.isLoading = true;
			this.error = "";
			try {
				this.booking = await fetchBookingDetails(bookingId);
			} catch (error) {
				this.error = error?.message || "Could not load booking details.";
			} finally {
				this.isLoading = false;
			}
		},
		async retry(bookingId) {
			await this.fetchBooking(bookingId);
		},
	},
});
