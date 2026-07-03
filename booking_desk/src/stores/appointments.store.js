import { defineStore } from "pinia";
import {
	fetchAppointmentsWorkspace,
	fetchAppointmentMetrics,
} from "@/services/appointments.service";

function createEmptyFilters() {
	return {
		searchText: "",
		customerQuery: "",
		bookingReference: "",
		statuses: [],
		paymentStatuses: [],
		provider: "",
		fromDate: "",
		toDate: "",
	};
}

function createEmptyMetrics() {
	return {
		total: 0,
		inProgress: 0,
		checkedIn: 0,
		completed: 0,
		pendingPayment: 0,
		delayed: 0,
	};
}

export const useAppointmentsStore = defineStore("appointmentsWorkspace", {
	state: () => ({
		appointments: [],
		selectedAppointment: null,
		metrics: createEmptyMetrics(),
		filters: createEmptyFilters(),
		page: 1,
		pageSize: 24,
		hasMore: false,
		isLoading: false,
		isRefreshing: false,
		error: "",
		providerOptions: [],
		statusOptions: [],
		paymentStatusOptions: [],
		debounceTimer: null,
	}),
	getters: {
		filteredAppointments: (state) => state.appointments,
		groupedAppointments: (state) => {
			return state.appointments.reduce((groups, appointment) => {
				const key = appointment.appointmentDate || "Unknown";
				if (!groups[key]) {
					groups[key] = [];
				}
				groups[key].push(appointment);
				return groups;
			}, {});
		},
		activeAppointments: (state) =>
			state.appointments.filter((appointment) =>
				["Checked In", "In Progress"].includes(appointment.status)
			),
		delayedAppointments: (state) =>
			state.appointments.filter((appointment) => appointment.status === "Rescheduled"),
	},
	actions: {
		setSelectedAppointment(appointment) {
			this.selectedAppointment = appointment || null;
		},
		updateFilters(patch = {}, { debounceMs = 0 } = {}) {
			this.filters = { ...this.filters, ...patch };
			if (debounceMs > 0) {
				clearTimeout(this.debounceTimer);
				this.debounceTimer = setTimeout(() => {
					this.fetchAppointments({ page: 1 });
				}, debounceMs);
				return;
			}
			this.fetchAppointments({ page: 1 });
		},
		resetFilters() {
			this.filters = createEmptyFilters();
		},
		async fetchAppointments({ page = 1 } = {}) {
			this.isLoading = true;
			this.error = "";
			try {
				const payload = await fetchAppointmentsWorkspace({
					...this.filters,
					page,
					pageSize: this.pageSize,
				});

				this.appointments = payload.appointments;
				this.page = payload.page;
				this.pageSize = payload.pageSize;
				this.hasMore = payload.hasMore;
			} catch (error) {
				this.error = error?.message || "Could not load appointments.";
			} finally {
				this.isLoading = false;
			}
		},
		async fetchMetrics() {
			this.isRefreshing = true;
			try {
				const payload = await fetchAppointmentMetrics({ ...this.filters });
				this.metrics = payload.metrics;
				this.providerOptions = payload.providerOptions;
				this.statusOptions = payload.statusOptions;
				this.paymentStatusOptions = payload.paymentStatusOptions;
			} catch (error) {
				if (!this.error) {
					this.error = error?.message || "Could not load appointment metrics.";
				}
			} finally {
				this.isRefreshing = false;
			}
		},
		async refreshAppointments() {
			await Promise.all([this.fetchAppointments({ page: 1 }), this.fetchMetrics()]);
		},
		async retry() {
			await this.refreshAppointments();
		},
	},
});
