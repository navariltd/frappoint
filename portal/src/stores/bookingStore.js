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
			price: null,
			currency: null,
			notes: null,
			source: "Portal",
		},
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
				state.draft.price
			),
	},

	actions: {
		setServiceType(serviceType) {
			this.draft.serviceType = serviceType;
		},

		setDate(date) {
			this.draft.date = date;
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
	},
});
