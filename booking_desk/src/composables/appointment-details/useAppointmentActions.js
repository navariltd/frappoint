import { computed } from "vue";
import { useAppointmentDetailsStore } from "@/stores/appointmentDetails.store";

export function useAppointmentActions() {
	const store = useAppointmentDetailsStore();
	const busy = computed(() => store.isSubmittingAction);

	const checkIn = (appointmentId = store.appointment.appointmentId) =>
		store.performAction({ appointmentId, action: "check_in" });

	const start = (appointmentId = store.appointment.appointmentId) =>
		store.performAction({ appointmentId, action: "start" });

	const complete = (appointmentId = store.appointment.appointmentId) =>
		store.performAction({ appointmentId, action: "complete" });

	const confirm = (appointmentId = store.appointment.appointmentId) =>
		store.performAction({ appointmentId, action: "confirm" });

	const cancel = (appointmentId = store.appointment.appointmentId, cancellationReasons = []) =>
		store.performAction({
			appointmentId,
			action: "cancel",
			cancellationReasons,
		});

	const reschedule = (payload = {}) =>
		store.performAction({
			appointmentId: payload.appointmentId || store.appointment.appointmentId,
			action: payload.action || "reschedule",
			newAppointmentDate: payload.newAppointmentDate,
			newStartTime: payload.newStartTime,
			newEndTime: payload.newEndTime,
			newProvider: payload.newProvider,
			newSlotIds: payload.newSlotIds,
			newServiceUnit: payload.newServiceUnit,
		});

	const reassignProvider = (provider) =>
		reschedule({
			action: "reassign_provider",
			newAppointmentDate: store.appointment.appointmentDate,
			newStartTime: store.appointment.startTime,
			newEndTime: store.appointment.endTime,
			newProvider: provider,
		});

	const editTimeSlot = ({ date, startTime, endTime, provider, slotIds, serviceUnit }) =>
		reschedule({
			action: "edit_time_slot",
			newAppointmentDate: date,
			newStartTime: startTime,
			newEndTime: endTime,
			newProvider: provider,
			newSlotIds: slotIds,
			newServiceUnit: serviceUnit,
		});

	return {
		busy,
		checkIn,
		start,
		complete,
		confirm,
		cancel,
		reschedule,
		reassignProvider,
		editTimeSlot,
	};
}
