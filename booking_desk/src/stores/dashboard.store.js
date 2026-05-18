import { defineStore } from "pinia";
import {
	fetchDashboardMetrics,
	getDateRangeByView,
	toIsoDate,
} from "@/services/dashboard.service";
import { fetchTimelineDataset } from "@/services/timeline.service";

const defaultMetrics = () => ({
	todayAppointments: 0,
	checkedIn: 0,
	ongoing: 0,
	pendingPayment: 0,
	delayed: 0,
	noShow: 0,
});

const makeCacheKey = (view, selectedDate) => `${view}:${selectedDate}`;

export const useDashboardStore = defineStore("dashboard", {
	state: () => ({
		selectedDate: toIsoDate(new Date()),
		view: "day",
		metrics: defaultMetrics(),
		providers: [],
		appointments: [],
		isLoading: false,
		error: null,
		lastFetchedAt: null,
		_cache: {},
	}),
	actions: {
		setDate(date) {
			this.selectedDate = date;
		},
		setView(view) {
			this.view = view;
		},
		applyLocalAppointmentUpdates(nextAppointments) {
			this.appointments = nextAppointments;
		},
		async refresh({ force = false } = {}) {
			const key = makeCacheKey(this.view, this.selectedDate);

			if (!force && this._cache[key]) {
				this.metrics = this._cache[key].metrics;
				this.providers = this._cache[key].providers;
				this.appointments = this._cache[key].appointments;
				return;
			}

			this.isLoading = true;
			this.error = null;

			try {
				const { fromDate, toDate } = getDateRangeByView(this.selectedDate, this.view);
				const [metrics, timeline] = await Promise.all([
					fetchDashboardMetrics(this.selectedDate),
					fetchTimelineDataset({ fromDate, toDate }),
				]);

				this.metrics = metrics;
				this.providers = timeline.providers;
				this.appointments = timeline.appointments;
				this.lastFetchedAt = new Date().toISOString();
				this._cache[key] = {
					metrics,
					providers: timeline.providers,
					appointments: timeline.appointments,
				};
			} catch (error) {
				this.error = error?.message || "Failed to load dashboard data";
			} finally {
				this.isLoading = false;
			}
		},
	},
});
