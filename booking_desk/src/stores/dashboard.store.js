import { defineStore } from "pinia";
import {
	fetchDashboardMetrics,
	getDateRangeByView,
	toIsoDate,
} from "@/services/dashboard.service";
import { fetchTimelineDataset } from "@/services/timeline.service";
import {
	CACHE_MAX_AGE,
	CACHE_TAGS,
	getMemoryCache,
	setMemoryCache,
	sweepExpiredMemoryCache,
} from "@/utils/cachePolicy";

const defaultMetrics = () => ({
	todayAppointments: 0,
	checkedIn: 0,
	ongoing: 0,
	completed: 0,
	pendingPayment: 0,
	cancelled: 0,
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
		cacheMaxAge: CACHE_MAX_AGE.DASHBOARD,
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
			sweepExpiredMemoryCache();
			const key = makeCacheKey(this.view, this.selectedDate);
			const cacheKey = `dashboard:${key}`;

			if (!force) {
				const snapshot = getMemoryCache(cacheKey);
				if (snapshot) {
					this.metrics = snapshot.metrics;
					this.providers = snapshot.providers;
					this.appointments = snapshot.appointments;
					this.lastFetchedAt = new Date(snapshot.createdAt).toISOString();
					return;
				}
			}

			if (force) {
				this.lastFetchedAt = null;
			}

			if (!force && this.isLoading) {
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
				const createdAt = Date.now();
				this.lastFetchedAt = new Date(createdAt).toISOString();
				setMemoryCache(
					cacheKey,
					{
						metrics,
						providers: timeline.providers,
						appointments: timeline.appointments,
						createdAt,
					},
					{
						maxAge: this.cacheMaxAge,
						tags: [CACHE_TAGS.DASHBOARD, CACHE_TAGS.BOOKINGS],
					}
				);
			} catch (error) {
				this.error = error?.message || "Failed to load dashboard data";
			} finally {
				this.isLoading = false;
			}
		},
	},
});
