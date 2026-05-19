import { computed } from "vue";

export function useAvailability(storeRefs) {
	const hasDateAvailability = computed(() => (guest) => guest.availableDates.length > 0);
	const hasSlotAvailability = computed(() => (guest) => guest.availableSlots.length > 0);
	const isLoadingDatesForGuest = computed(
		() => (guestKey) => Boolean(storeRefs.isLoadingDates.value[guestKey])
	);
	const isLoadingSlotsForGuest = computed(
		() => (guestKey) => Boolean(storeRefs.isLoadingSlots.value[guestKey])
	);
	const guestError = computed(() => (guestKey) => storeRefs.errorByGuest.value[guestKey] || "");

	return {
		hasDateAvailability,
		hasSlotAvailability,
		isLoadingDatesForGuest,
		isLoadingSlotsForGuest,
		guestError,
	};
}
