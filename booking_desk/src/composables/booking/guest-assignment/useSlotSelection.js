import { computed } from "vue";

export function useSlotSelection(assignments) {
	const selectedSlotCount = computed(() =>
		assignments.value.reduce(
			(sum, service) => sum + service.guests.filter((guest) => guest.slot).length,
			0
		)
	);

	const pendingSlotCount = computed(() =>
		assignments.value.reduce(
			(sum, service) => sum + service.guests.filter((guest) => !guest.slot).length,
			0
		)
	);

	return {
		selectedSlotCount,
		pendingSlotCount,
	};
}
