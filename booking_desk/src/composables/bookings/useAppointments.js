import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useAppointmentsStore } from "@/stores/appointments.store";

export function useAppointments() {
	const store = useAppointmentsStore();
	const refs = storeToRefs(store);

	onMounted(() => {
		store.refreshAppointments();
	});

	const hasAppointments = computed(() => refs.appointments.value.length > 0);

	return {
		...refs,
		hasAppointments,
		refreshAppointments: store.refreshAppointments,
		fetchAppointments: store.fetchAppointments,
		fetchMetrics: store.fetchMetrics,
		updateFilters: store.updateFilters,
		resetFilters: store.resetFilters,
		retry: store.retry,
		setSelectedAppointment: store.setSelectedAppointment,
	};
}
