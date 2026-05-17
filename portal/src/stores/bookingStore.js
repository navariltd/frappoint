import { createResource } from "frappe-ui";
import { defineStore } from "pinia";

export const useBookingStore = defineStore("booking", {
	state: () => ({
		draft: {
			serviceType: null,
			duration: null,
			date: null,
			slot: null,
			provider: null,
			customer: null,
			fullName: null,
			email: null,
			mobileNo: null,
			priceName: null,
			price: null,
			currency: null,
			notes: null,
			couponCode: null,
			paymentGateways: [],
			selectedPaymentGateway: null,
			source: "Portal",
			numberOfGuests: 1,
			guests: [],
			appointments: [],
			minGuests: 1,
			maxGuests: null,
		},
		serviceDetails: null,

		currentStep: 1,
		attemptedCheckout: false,
		isResetting: false,
	}),

	getters: {
		isComplete: (state) => {
			const hasBasicInfo = !!(
				state.draft.serviceType &&
				state.draft.date &&
				state.draft.slot &&
				state.draft.fullName &&
				state.draft.mobileNo &&
				state.draft.email &&
				state.draft.priceName &&
				state.draft.price
			);

			// Check all guests have required full_name
			const allGuestsValid =
				state.draft.guests &&
				Array.isArray(state.draft.guests) &&
				state.draft.guests.length > 0 &&
				state.draft.guests.every((guest) => guest.full_name && guest.full_name.trim());

			return hasBasicInfo && allGuestsValid;
		},

		canAddMoreGuests: (state) => {
			// If maxGuests is null, allow unlimited guests
			if (!state.draft.maxGuests) {
				return true;
			}
			// Otherwise, check if current count is less than max
			return state.draft.guests.length < state.draft.maxGuests;
		},

		canRemoveGuest: (state) => {
			// Can only remove guests beyond the minimum required
			return state.draft.guests.length > state.draft.minGuests;
		},
	},

	actions: {
		setMode(mode) {
			this.mode = mode;
		},

		setServiceType(serviceType) {
			this.draft.serviceType = serviceType;
		},

		setDuration(duration) {
			this.draft.duration = duration;
		},

		setDate(date) {
			let formattedDate = date;
			// Convert Date object to YYYY-MM-DD string format if needed
			if (date instanceof Date) {
				const year = date.getFullYear();
				const month = String(date.getMonth() + 1).padStart(2, "0");
				const day = String(date.getDate()).padStart(2, "0");
				formattedDate = `${year}-${month}-${day}`;
			}

			this.draft.date = formattedDate;
		},
		setSlot(slot) {
			this.draft.slot = slot;
		},

		setProvider(provider) {
			this.draft.provider = provider;
		},

		setCustomer(customer) {
			this.draft.customer = customer;
		},

		setFullName(fullName) {
			this.draft.fullName = fullName;
		},

		setMobileNo(mobileNo) {
			this.draft.mobileNo = mobileNo;
		},

		setEmail(email) {
			this.draft.email = email;
		},

		setPriceName(priceName) {
			this.draft.priceName = priceName;
		},

		setPrice(price) {
			this.draft.price = price;
		},

		setCurrency(currency) {
			this.draft.currency = currency;
		},

		setPaymentGateways(gateways) {
			this.draft.paymentGateways = gateways || [];
		},

		selectPaymentGateway(gateway) {
			this.draft.selectedPaymentGateway = gateway;
		},

		setNumberOfGuests(count) {
			this.draft.numberOfGuests = count;
			this.initializeGuests();
		},

		initializeGuests() {
			// Use minGuests as the required count, not numberOfGuests
			const count = this.draft.minGuests || this.draft.numberOfGuests || 1;

			// Keep existing guest data where possible
			const existingGuests = [...this.draft.guests];
			this.draft.guests = [];

			for (let i = 0; i < count; i++) {
				const existingGuest = existingGuests[i];

				// Keep existing guest data if available, otherwise create empty guest
				this.draft.guests.push(
					existingGuest || {
						full_name: "",
						email: "",
						mobile_no: "",
						is_primary: i === 0 ? 1 : 0,
						notes: "",
					}
				);
			}
		},

		updateGuest(index, field, value) {
			if (this.draft.guests[index]) {
				this.draft.guests[index][field] = value;
			}
		},

		addGuest() {
			// Check if we can add more guests
			if (this.draft.maxGuests && this.draft.guests.length >= this.draft.maxGuests) {
				return; // Cannot exceed max guests
			}

			this.draft.guests.push({
				full_name: "",
				email: "",
				mobile_no: "",
				is_primary: 0,
				notes: "",
			});
		},

		createAppointmentSnapshot() {
			return {
				appointment_type: this.draft.serviceType,
				price_id: this.draft.priceName,
				date: this.draft.date,
				duration: this.draft.duration,
				slot: this.draft.slot ? { ...this.draft.slot } : {},
				currency: this.draft.currency,
				price: this.draft.price,
				customer: this.draft.customer,
				full_name: this.draft.fullName,
				email: this.draft.email,
				mobile_no: this.draft.mobileNo,
				guest_full_name: this.draft.fullName,
				guest_email: this.draft.email,
				guest_mobile_no: this.draft.mobileNo,
				selected_payment_gateway: this.draft.selectedPaymentGateway,
				notes: this.draft.notes,
				coupon_code: this.draft.couponCode,
				source: this.draft.source,
				is_primary: 1,
				guests: (this.draft.guests || []).map((guest) => ({ ...guest })),
			};
		},

		resetCurrentAppointmentDraft() {
			this.draft.date = null;
			this.draft.slot = null;
			this.draft.provider = null;
			this.draft.customer = null;
			this.draft.fullName = null;
			this.draft.email = null;
			this.draft.mobileNo = null;
			this.draft.notes = null;
			this.draft.couponCode = null;
			this.draft.numberOfGuests = this.draft.minGuests || 1;
			this.draft.guests = [];
			this.initializeGuests();
		},

		// Appointment basket helpers for multi-appointment booking
		addAppointmentToBasket({ resetCurrent = false } = {}) {
			const appt = this.createAppointmentSnapshot();
			this.draft.appointments = this.draft.appointments || [];
			this.draft.appointments.push(appt);
			if (resetCurrent) {
				this.resetCurrentAppointmentDraft();
			}
			this.saveToStorage();
			return appt;
		},

		removeAppointmentFromBasket(index) {
			if (!this.draft.appointments) return;
			this.draft.appointments.splice(index, 1);
			this.saveToStorage();
		},

		clearAppointmentBasket() {
			this.draft.appointments = [];
			this.saveToStorage();
		},

		removeGuest(index) {
			if (this.draft.guests.length <= this.draft.minGuests) {
				return; // Cannot go below minimum
			}

			this.draft.guests.splice(index, 1);
		},

		syncPrimaryGuest() {
			// Sync primary guest data from main form fields
			if (this.draft.guests.length > 0) {
				this.draft.guests[0] = {
					...this.draft.guests[0],
					full_name: this.draft.fullName,
					email: this.draft.email,
					mobile_no: this.draft.mobileNo,
					is_primary: 1,
				};
			}
		},

		async hydrateServiceDetails() {
			const resource = createResource({
				url: "frappoint.frappoint.api.service_type.get_service_type_details",
				method: "GET",
				makeParams: () => ({
					service_type: this.draft.serviceType,
				}),
			});

			const service = await resource.fetch();
			this.serviceDetails = service;

			this.draft.paymentGateways = service.payment_gateways || [];
			this.draft.minGuests = service.min_guests || 1;
			this.draft.maxGuests = service.max_guests || null;

			if (!this.draft.selectedPaymentGateway && this.draft.paymentGateways.length === 1) {
				this.draft.selectedPaymentGateway = this.draft.paymentGateways[0];
			}

			// Initialize guests after setting minGuests from service
			this.initializeGuests();
		},

		initializeForReschedule(serviceType) {
			this.mode = "rescheduling";

			this.rescheduleDraft = {
				serviceType: serviceType,
				date: null,
				slot: null,
				provider: null,
			};
		},
		initializeForBooking() {
			this.mode = "booking";
			this.loadFromStorage();
		},

		resetBooking() {
			this.draft = {
				serviceType: null,
				duration: null,
				date: null,
				slot: null,
				provider: null,
				customer: null,
				fullName: null,
				email: null,
				mobileNo: null,
				priceName: null,
				price: null,
				currency: null,
				notes: null,
				couponCode: null,
				selectedPaymentGateway: null,
				paymentGateways: [],
				source: "Portal",
				numberOfGuests: 1,
				guests: [],
				appointments: [],
				minGuests: 1,
				maxGuests: null,
			};
			this.serviceDetails = null;
			this.mode = "booking";
		},

		// Save to localStorage to persist even on refresh
		saveToStorage() {
			localStorage.setItem("bookingDraft", JSON.stringify(this.draft));
		},

		loadFromStorage() {
			const draft = localStorage.getItem("bookingDraft");
			if (draft) {
				this.draft = JSON.parse(draft);

				// Ensure new fields exist with defaults
				if (!this.draft.numberOfGuests) {
					this.draft.numberOfGuests = 1;
				}
				if (!this.draft.guests || !Array.isArray(this.draft.guests)) {
					this.draft.guests = [];
				}
				if (!this.draft.appointments || !Array.isArray(this.draft.appointments)) {
					this.draft.appointments = [];
				}
				if (!this.draft.minGuests) {
					this.draft.minGuests = 1;
				}
				if (!this.draft.maxGuests) {
					this.draft.maxGuests = null;
				}
				if (this.draft.couponCode === undefined) {
					this.draft.couponCode = null;
				}
			}
		},

		clearStorage() {
			localStorage.removeItem("bookingDraft");
		},
	},
});
