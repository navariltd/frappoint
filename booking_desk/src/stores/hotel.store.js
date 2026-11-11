import { defineStore } from "pinia";
import { fetchDeskContextApi, fetchSessionContextApi, hotelErrorMessage } from "@/api/hotel.api";

const PROPERTY_KEY = "frappoint.hotel.property";

function readSavedProperty() {
	try {
		return window.localStorage.getItem(PROPERTY_KEY) || null;
	} catch {
		return null;
	}
}

export const useHotelStore = defineStore("hotel", {
	state: () => ({
		enabled: false,
		roles: [],
		properties: [],
		bookingSources: [],
		holdExpiryMinutes: 15,
		maxStayNights: 30,
		canBook: false,
		property: readSavedProperty(),
		loaded: false,
		loading: false,
		error: null,
	}),

	getters: {
		currentProperty: (state) =>
			state.properties.find((p) => p.name === state.property) || null,
	},

	actions: {
		/** Load once per page load: is hospitality on, and what may this user book. */
		async load(force = false) {
			if ((this.loaded && !force) || this.loading) return;
			this.loading = true;
			this.error = null;
			try {
				const session = await fetchSessionContextApi();
				this.enabled = !!session?.enabled;
				this.roles = session?.roles || [];
				if (this.enabled && this.roles.length) {
					const context = await fetchDeskContextApi();
					this.properties = context?.properties || [];
					this.bookingSources = context?.booking_sources || [];
					this.holdExpiryMinutes = context?.hold_expiry_minutes || 15;
					this.maxStayNights = context?.max_stay_nights || 30;
					this.canBook = !!context?.can_book;
					if (!this.currentProperty) this.setProperty(this.properties[0]?.name || null);
				}
			} catch (error) {
				this.error = hotelErrorMessage(error);
			} finally {
				this.loading = false;
				this.loaded = true;
			}
		},

		setProperty(name) {
			this.property = name;
			try {
				if (name) window.localStorage.setItem(PROPERTY_KEY, name);
			} catch {
				// Private mode or blocked storage: the choice just isn't remembered.
			}
		},
	},
});
