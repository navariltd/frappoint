import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useBookingWorkflowStore } from "@/stores/bookingWorkflow.store";

export function useDraftAppointments() {
	const store = useBookingWorkflowStore();
	store.hydrateFromStorage();

	const { appointmentsByGuestKey, isSavingAppointmentByGuest, appointmentErrorByGuest } =
		storeToRefs(store);

	const isSavingAppointment = computed(
		() => (guestKey) => Boolean(isSavingAppointmentByGuest.value[guestKey])
	);
	const appointmentError = computed(
		() => (guestKey) => appointmentErrorByGuest.value[guestKey] || ""
	);
	const appointmentForGuest = computed(
		() => (guestKey) => appointmentsByGuestKey.value[guestKey] || null
	);

	return {
		appointmentsByGuestKey,
		isSavingAppointmentByGuest,
		appointmentErrorByGuest,
		isSavingAppointment,
		appointmentError,
		appointmentForGuest,
		upsertDraftAppointment: store.upsertDraftAppointment,
		clearAppointmentError: store.clearAppointmentError,
	};
}
