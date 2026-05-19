import { defineStore } from "pinia";
import { fetchBookingsWorkspace } from "@/services/bookings.service";
import {
	BOOKING_VIEWS,
	BOOKING_STATUSES,
	PAYMENT_STATUSES,
	createEmptyBookingsState,
} from "@/types/bookings";

export const useBookingsStore = defineStore("bookingsWorkspace", {
	state: () => createEmptyBookingsState(),
	getters: {
		isBookingsView(state) {
			return state.selectedView === BOOKING_VIEWS.BOOKINGS;
		},
		statusOptions() {
			return BOOKING_STATUSES;
		},
		paymentStatusOptions() {
			return PAYMENT_STATUSES;
		},
		summary(state) {
			const total = state.bookings.length;
			const pendingPayment = state.bookings.filter(
				(booking) => booking.paymentStatus !== "Paid"
			).length;
			const checkedIn = state.bookings.filter(
				(booking) => booking.status === "Checked In"
			).length;
			return { total, pendingPayment, checkedIn };
		},
	},
	actions: {
		setView(view) {
			this.selectedView = view;
		},
		setFilters(patch = {}) {
			this.filters = { ...this.filters, ...patch };
		},
		resetFilters() {
			this.filters = createEmptyBookingsState().filters;
		},
		async fetchBookings({ page = 1 } = {}) {
			this.isLoading = true;
			this.error = "";
			try {
				const payload = await fetchBookingsWorkspace({
					...this.filters,
					page,
					pageSize: this.pageSize,
				});
				this.bookings = payload.bookings;
				this.page = payload.page;
				this.pageSize = payload.pageSize;
				this.hasMore = payload.hasMore;
			} catch (error) {
				this.error = error?.message || "Could not load bookings workspace.";
			} finally {
				this.isLoading = false;
			}
		},
		async retry() {
			await this.fetchBookings({ page: this.page || 1 });
		},
	},
});
