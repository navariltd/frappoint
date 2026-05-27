import { createResource } from "frappe-ui";
import { defineStore } from "pinia";

export const useBookingStore = defineStore("booking", {
	state: () => ({
		// Global Customer (The person booking/paying)
		customer: {
			customer: "",
			fullName: "",
			email: "",
			mobileNo: "",
		},

		// Booking-level configuration
		bookingConfig: {
			is_group: false,
			same_service: false,
			same_time: false,
			min_guests: 1,

			// shared values
			service: null,
			date: null,
			slot: null,
		},

		// List of Guests - Each guest is an independent booking unit
		guests: [],

		// UI State
		currentStep: 1,
		selectedGuestIndex: 0,

		paymentGateways: [],
		selectedPaymentGateway: null,

		loading: false,
	}),

	getters: {
		totalAmount: (state) => {
			return state.guests.reduce((sum, guest) => sum + (guest.amount || 0), 0);
		},

		isComplete: (state) => {
			if (state.guests.length === 0) return false;

			const guestsValid = state.guests.every(
				(guest) =>
					guest.guest_full_name && guest.appointment_type && guest.slot && guest.date
			);

			const customerValid = !!(state.customer.fullName || state.customer.mobileNo);

			return guestsValid && customerValid;
		},
	},

	actions: {
		addGuest(details = {}) {
			this.guests.push({
				// Identity
				guest_full_name: details.guest_full_name || "",
				guest_email: details.guest_email || "",
				guest_mobile_no: details.guest_mobile_no || "",
				is_primary: this.guests.length === 0 ? 1 : 0,

				// Service selection
				appointment_type: details.appointment_type || null,
				price_id: details.price_id || null,
				duration: details.duration || 0,
				amount: details.amount || 0,
				currency: details.currency || "KES",

				// Timing
				date: details.date || null,
				slot: details.slot || null,
				provider: details.provider || null,

				notes: "",
			});
		},

		removeGuest(index) {
			if (this.guests.length > 1) {
				this.guests.splice(index, 1);
			}
		},

		cloneGuest(index) {
			const guest = this.guests[index];
			if (guest) {
				this.guests.push({ ...guest, is_primary: 0 });
			}
		},

		updateGuest(index, data) {
			if (this.guests[index]) {
				this.guests[index] = { ...this.guests[index], ...data };
			}
		},

		setCustomer(data) {
			this.customer = { ...this.customer, ...data };
		},

		setBookingConfig(config) {
			this.bookingConfig = { ...this.bookingConfig, ...config };
		},

		applyServiceToAll(service) {
			this.bookingConfig.same_service = true;
			this.bookingConfig.service = service;
		},

		applyTimeToAll(date, slot) {
			this.bookingConfig.same_time = true;
			this.bookingConfig.date = date;
			this.bookingConfig.slot = slot;
		},

		setPaymentGateways(gateways) {
			this.paymentGateways = gateways || [];
		},

		saveToStorage() {
			// Legacy store persistence retired in favor of workflow store.
		},

		loadFromStorage() {
			// Legacy store persistence retired in favor of workflow store.
			this.guests = this.guests || [];
		},

		async submitBooking() {
			const bookingResource = createResource({
				url: "frappoint.frappoint.api.booking_desk.create_booking",
				onSuccess: (data) => {
					alert("Booking Successful!");
					this.resetStore();
				},
				onError: (error) => {
					const msg = error.messages?.[0] || "Booking Failed";
					alert("Booking Failed: " + msg);
				},
			});

			this.loading = true;

			try {
				await bookingResource.submit({
					customer: this.customer,
					guests: this.guests,
				});
			} catch (e) {
				console.error("Submission error:", e);
			} finally {
				this.loading = false;
			}
		},

		resetStore() {
			this.customer = { fullName: "", email: "", mobileNo: "" };
			this.guests = [];
			this.currentStep = 1;
		},
	},
});
