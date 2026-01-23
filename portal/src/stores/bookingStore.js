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
			source: "Portal",
		},
		currentStep: 1,
		attemptedCheckout: false,
		isResetting: false,
	}),

	getters: {
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
	},

	actions: {
		setServiceType(serviceType) {
			this.draft.serviceType = serviceType;
		},

		setDate(date) {
			// Convert Date object to YYYY-MM-DD string format if needed
			if (date instanceof Date) {
				const year = date.getFullYear();
				const month = String(date.getMonth() + 1).padStart(2, "0");
				const day = String(date.getDate()).padStart(2, "0");
				this.draft.date = `${year}-${month}-${day}`;
			} else {
				this.draft.date = date;
			}
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
				source: "Portal",
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
