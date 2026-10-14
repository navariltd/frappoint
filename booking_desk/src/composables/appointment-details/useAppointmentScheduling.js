import { computed } from "vue";
import { useAppointmentDetailsStore } from "@/stores/appointmentDetails.store";

export function useAppointmentScheduling() {
	const store = useAppointmentDetailsStore();

	const dates = computed(() => store.availabilityDates);
	const slots = computed(() => store.availabilitySlots);
	const selectedDate = computed(() => store.selectedAvailabilityDate);
	const selectedSlotId = computed(() => store.selectedAvailabilitySlotId);
	const selectedSlot = computed(
		() =>
			store.availabilitySlots.find((slot) => slot.id === store.selectedAvailabilitySlotId) ||
			null
	);

	const selectDate = async (date) => {
		store.setSelectedAvailabilityDate(date);
		await store.refreshAvailability();
	};

	const selectSlot = (slot) => {
		store.setSelectedAvailabilitySlot(slot);
	};

	const applySelectedSlot = async () => {
		if (!selectedSlot.value) {
			return null;
		}
		if (store.appointment.isCouple && selectedSlot.value.isCouple) {
			const slot = selectedSlot.value;
			return store.performAction({
				action:
					Number(store.appointment.docstatus || 0) === 0
						? "edit_time_slot"
						: "reschedule",
				newAppointmentDate: slot.date,
				newStartTime: slot.startTime,
				coupleUpdate: {
					date: slot.date,
					start_time: slot.startTime,
					guest_1: {
						provider: slot.guest1.provider,
						service_unit: slot.guest1.serviceUnit,
						end_time: slot.guest1.endTime,
						slot_ids: slot.guest1.slotIds || [],
					},
					guest_2: {
						provider: slot.guest2.provider,
						service_unit: slot.guest2.serviceUnit,
						end_time: slot.guest2.endTime,
						slot_ids: slot.guest2.slotIds || [],
					},
				},
			});
		}
		return store.performAction({
			action: "reschedule",
			newAppointmentDate: selectedSlot.value.date,
			newStartTime: selectedSlot.value.startTime,
			newEndTime: selectedSlot.value.endTime,
			newProvider: selectedSlot.value.providers?.[0]?.provider || store.appointment.provider,
			newSlotIds:
				Array.isArray(selectedSlot.value.providers?.[0]?.slotIds) &&
				selectedSlot.value.providers[0].slotIds.length
					? selectedSlot.value.providers[0].slotIds
					: undefined,
			newServiceUnit:
				selectedSlot.value.providers?.[0]?.serviceUnit || store.appointment.serviceUnit,
		});
	};

	return {
		dates,
		slots,
		selectedDate,
		selectedSlotId,
		selectedSlot,
		selectDate,
		selectSlot,
		applySelectedSlot,
	};
}
