import { computed, onMounted, unref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useAppointmentDetailsStore } from "@/stores/appointmentDetails.store";

export function useAppointmentDetails(appointmentId = "") {
	const store = useAppointmentDetailsStore();
	const refs = storeToRefs(store);
	const appointmentIdRef = computed(() => unref(appointmentId));

	onMounted(() => {
		store.fetchAppointment(appointmentIdRef.value);
	});

	watch(appointmentIdRef, (value) => {
		if (value) {
			store.fetchAppointment(value);
		}
	});

	return {
		...refs,
		summary: computed(() => refs.appointment.value),
		financialSummary: computed(() => store.financialSummary),
		summaryMetrics: computed(() => store.summaryMetrics),
		hasAppointment: computed(() => store.hasAppointment),
		hasBookingContext: computed(() => store.hasBookingContext),
		retry: () => store.retry(appointmentIdRef.value),
	};
}
