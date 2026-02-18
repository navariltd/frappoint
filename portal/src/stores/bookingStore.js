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
			paymentGateways: [],
			selectedPaymentGateway: null,
			source: "Portal",
			numberOfGuests: 1,
			guests: [],
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
			const count = this.draft.numberOfGuests || 1;

			// Keep existing guest data where possible
			const existingGuests = [...this.draft.guests];
			this.draft.guests = [];

			for (let i = 0; i < count; i++) {
				const existingGuest = existingGuests[i];

				if (i === 0) {
					// Primary guest (contact person) pre-filled from main form
					this.draft.guests.push({
						full_name: this.draft.fullName || existingGuest?.full_name || "",
						email: this.draft.email || existingGuest?.email || "",
						mobile_no: this.draft.mobileNo || existingGuest?.mobile_no || "",
						is_primary: 1,
						notes: existingGuest?.notes || "",
					});
				} else {
					// Additional guests
					this.draft.guests.push(
						existingGuest || {
							full_name: "",
							email: "",
							mobile_no: "",
							is_primary: 0,
							notes: "",
						}
					);
				}
			}
		},

		updateGuest(index, field, value) {
			if (this.draft.guests[index]) {
				this.draft.guests[index][field] = value;

				// If updating primary guest, also update main form fields
				if (index === 0) {
					if (field === "full_name") this.draft.fullName = value;
					if (field === "email") this.draft.email = value;
					if (field === "mobile_no") this.draft.mobileNo = value;
				}
			}
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
				date: null,
				slot: null,
				provider: null,
				customer: null,
				email: null,
				mobileNo: null,
				priceName: null,
				price: null,
				notes: null,
				selectedPaymentGateway: null,
				paymentGateways: [],
				source: "Portal",
				numberOfGuests: 1,
				guests: [],
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
				if (!this.draft.minGuests) {
					this.draft.minGuests = 1;
				}
				if (!this.draft.maxGuests) {
					this.draft.maxGuests = null;
				}
			}
		},

		clearStorage() {
			localStorage.removeItem("bookingDraft");
		},
	},
});
