import { createResource } from "frappe-ui";
import { defineStore } from "pinia";

export const useBookingStore = defineStore("booking", {
	state: () => ({
		draft: {
			serviceType: null,
			date: null,
			slot: null,
			provider: null,
			customer: null,
			email: null,
			mobileNo: null,
			priceName: null,
			price: null,
			currency: null,
			notes: null,
			paymentGateways: [],
			selectedPaymentGateway: null,
			source: "Portal",
		},

		rescheduleDraft: {
			serviceType: null,
			date: null,
			slot: null,
			provider: null,
		},

		currentStep: 1,
		attemptedCheckout: false,
		isResetting: false,
		mode: "booking",
	}),

	getters: {
		activeDraft: (state) => {
			return state.mode === "rescheduling" ? state.rescheduleDraft : state.draft;
		},

		isComplete: (state) =>
			!!(
				state.draft.serviceType &&
				state.draft.date &&
				state.draft.slot &&
				state.draft.customer &&
				state.draft.mobileNo &&
				state.draft.email &&
				state.draft.priceName &&
				state.draft.price
			),

		isRescheduleComplete: (state) =>
			!!(state.draft.serviceType && state.draft.date && state.draft.slot),
	},

	actions: {
		setMode(mode) {
			this.mode = mode;
		},

		setServiceType(serviceType) {
			if (this.mode === "rescheduling") {
				this.rescheduleDraft.serviceType = serviceType;
			} else {
				this.draft.serviceType = serviceType;
			}
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

			if (this.mode === "rescheduling") {
				this.rescheduleDraft.date = formattedDate;
			} else {
				this.draft.date = formattedDate;
			}
		},
		setSlot(slot) {
			if (this.mode === "rescheduling") {
				this.rescheduleDraft.slot = slot;
			} else {
				this.draft.slot = slot;
			}
		},

		setProvider(provider) {
			if (this.mode === "rescheduling") {
				this.rescheduleDraft.provider = provider;
			} else {
				this.draft.provider = provider;
			}
		},

		setCustomer(customer) {
			this.draft.customer = customer;
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

		async hydrateServiceDetails() {
			const serviceType =
				this.mode === "rescheduling"
					? this.rescheduleDraft.serviceType
					: this.draft.serviceType;

			if (!serviceType) return;

			const resource = createResource({
				url: "frappoint.frappoint.api.service_type.get_service_type_details",
				makeParams: () => ({
					service_type: this.draft.serviceType,
				}),
			});

			const service = await resource.fetch();

			if (this.mode === "booking") {
				this.draft.paymentGateways = service.payment_gateways || [];

				if (
					!this.draft.selectedPaymentGateway &&
					this.draft.paymentGateways.length === 1
				) {
					this.draft.selectedPaymentGateway = this.draft.paymentGateways[0];
				}
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
			};
			this.mode = "booking";
		},

		resetReschedule() {
			this.rescheduleDraft = {
				serviceType: null,
				date: null,
				slot: null,
				provider: null,
			};
		},

		// Save to localStorage to persist even on refresh
		saveToStorage() {
			localStorage.setItem("bookingDraft", JSON.stringify(this.draft));
		},

		loadFromStorage() {
			const draft = localStorage.getItem("bookingDraft");
			if (draft) this.draft = JSON.parse(draft);
		},

		clearStorage() {
			localStorage.removeItem("bookingDraft");
		},
	},
});
