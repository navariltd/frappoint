import { defineStore } from "pinia";
import { fetchCalendarEvents, runCalendarAppointmentAction } from "@/services/calendar.service";

function isoDate(date) {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");
	return `${year}-${month}-${day}`;
}

function parseIsoDate(value) {
	const date = new Date(`${value}T12:00:00`);
	return Number.isNaN(date.getTime()) ? new Date() : date;
}

function startOfWeek(date) {
	const result = new Date(date);
	const day = result.getDay();
	const diff = day === 0 ? -6 : 1 - day;
	result.setDate(result.getDate() + diff);
	return result;
}

function endOfWeek(date) {
	const start = startOfWeek(date);
	const result = new Date(start);
	result.setDate(start.getDate() + 6);
	return result;
}

function startOfMonth(date) {
	return new Date(date.getFullYear(), date.getMonth(), 1);
}

function endOfMonth(date) {
	return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

function emptyFilters() {
	return {
		searchText: "",
		customerQuery: "",
		statuses: [],
		provider: "",
		resource: "",
		fromDate: "",
		toDate: "",
	};
}

export const useCalendarStore = defineStore("calendarWorkspace", {
	state: () => ({
		events: [],
		selectedEvent: null,
		activeView: "week",
		anchorDate: isoDate(new Date()),
		filters: emptyFilters(),
		isLoading: false,
		isActionLoading: false,
		error: "",
		providerOptions: [],
		resourceOptions: [],
		statusOptions: [],
		debounceTimer: null,
	}),
	getters: {
		hasEvents: (state) => state.events.length > 0,
		visibleRange(state) {
			const anchor = parseIsoDate(state.anchorDate);
			if (state.activeView === "day") {
				return { fromDate: isoDate(anchor), toDate: isoDate(anchor) };
			}
			if (state.activeView === "month") {
				return {
					fromDate: isoDate(startOfMonth(anchor)),
					toDate: isoDate(endOfMonth(anchor)),
				};
			}
			return { fromDate: isoDate(startOfWeek(anchor)), toDate: isoDate(endOfWeek(anchor)) };
		},
	},
	actions: {
		setView(view) {
			if (!["day", "week", "month"].includes(view)) {
				return;
			}
			this.activeView = view;
			this.fetchEvents();
		},
		goToday() {
			this.anchorDate = isoDate(new Date());
			this.fetchEvents();
		},
		goPrev() {
			const anchor = parseIsoDate(this.anchorDate);
			if (this.activeView === "day") {
				anchor.setDate(anchor.getDate() - 1);
			} else if (this.activeView === "month") {
				anchor.setMonth(anchor.getMonth() - 1);
			} else {
				anchor.setDate(anchor.getDate() - 7);
			}
			this.anchorDate = isoDate(anchor);
			this.fetchEvents();
		},
		goNext() {
			const anchor = parseIsoDate(this.anchorDate);
			if (this.activeView === "day") {
				anchor.setDate(anchor.getDate() + 1);
			} else if (this.activeView === "month") {
				anchor.setMonth(anchor.getMonth() + 1);
			} else {
				anchor.setDate(anchor.getDate() + 7);
			}
			this.anchorDate = isoDate(anchor);
			this.fetchEvents();
		},
		selectEvent(event) {
			this.selectedEvent = event || null;
		},
		clearSelectedEvent() {
			this.selectedEvent = null;
		},
		updateFilters(patch = {}, { debounceMs = 0 } = {}) {
			this.filters = { ...this.filters, ...patch };
			if (debounceMs > 0) {
				clearTimeout(this.debounceTimer);
				this.debounceTimer = setTimeout(() => this.fetchEvents(), debounceMs);
				return;
			}
			this.fetchEvents();
		},
		async performAction(action) {
			if (!this.selectedEvent?.appointmentId || !action) {
				return;
			}
			this.isActionLoading = true;
			this.error = "";
			try {
				let cancelCouple;
				if (
					action === "cancel" &&
					this.selectedEvent.isCouple &&
					typeof window !== "undefined"
				) {
					cancelCouple = window.confirm(
						"This appointment is part of a couple booking. Select OK to cancel both appointments, or Cancel to cancel only this appointment."
					);
				}
				await runCalendarAppointmentAction({
					appointmentId: this.selectedEvent.appointmentId,
					action,
					cancelCouple,
				});
				await this.fetchEvents();
				const refreshed = this.events.find(
					(event) => event.appointmentId === this.selectedEvent.appointmentId
				);
				this.selectedEvent = refreshed || null;
			} catch (error) {
				this.error = error?.message || "Could not process appointment action.";
			} finally {
				this.isActionLoading = false;
			}
		},
		async fetchEvents() {
			this.isLoading = true;
			this.error = "";
			try {
				const range = this.visibleRange;
				const payload = await fetchCalendarEvents({
					...this.filters,
					fromDate: range.fromDate,
					toDate: range.toDate,
				});
				this.events = payload.events;
				this.providerOptions = payload.providerOptions;
				this.resourceOptions = payload.resourceOptions;
				this.statusOptions = payload.statusOptions;
			} catch (error) {
				this.error = error?.message || "Could not load calendar events.";
			} finally {
				this.isLoading = false;
			}
		},
		async retry() {
			await this.fetchEvents();
		},
	},
});
