import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useDashboardStore } from "@/stores/dashboard.store";

export function useProviderTimeline() {
	const store = useDashboardStore();
	const { providers, appointments, selectedDate, view, isLoading, error } = storeToRefs(store);

	const statusColors = {
		open: "bg-primary-container",
		"pending payment": "bg-tertiary-container",
		confirmed: "bg-secondary-fixed",
		"checked-in": "bg-secondary-fixed",
		ongoing: "bg-primary",
		rescheduled: "bg-error-container",
		completed: "bg-secondary-container",
		cancelled: "bg-surface-variant",
		closed: "bg-surface-variant",
		"no show": "bg-error",
	};

	const onAppointmentsUpdated = (nextAppointments) => {
		store.applyLocalAppointmentUpdates(nextAppointments);
	};

	const onDateChanged = async (date) => {
		store.setDate(date);
		await store.refresh();
	};

	const onViewChanged = async (nextView) => {
		store.setView(nextView);
		await store.refresh();
	};

	const timelineStatuses = computed(() => {
		const uniqueStatuses = Array.from(
			new Set(
				appointments.value.map((item) => String(item.status || "").trim()).filter(Boolean)
			)
		);

		return uniqueStatuses.map((status) => {
			const normalized = status.toLowerCase();
			return {
				key: status,
				label: status,
				color: statusColors[normalized] || "bg-primary-container",
			};
		});
	});

	return {
		providers,
		appointments,
		selectedDate,
		view,
		isLoading,
		error,
		timelineStatuses,
		onAppointmentsUpdated,
		onDateChanged,
		onViewChanged,
	};
}
