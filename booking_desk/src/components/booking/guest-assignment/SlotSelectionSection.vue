<template>
	<div class="space-y-2 border-t border-outline-variant pt-3">
		<p class="text-[11px] font-semibold uppercase tracking-wide text-on-surface">
			3. Select Slot
		</p>
		<p v-if="isLoading" class="text-[11px] text-on-surface-variant">
			Loading available slots...
		</p>
		<p v-else-if="error" class="text-[11px] text-error">{{ error }}</p>
		<p v-else-if="!slots.length" class="text-[11px] text-on-surface-variant">
			No slots available for this date.
		</p>
		<AvailableSlotsGrid
			v-else
			:slots="slots"
			:selectedSlotId="selectedSlotId"
			@select-slot="$emit('select-slot', $event)"
		/>
	</div>
</template>

<script setup>
import AvailableSlotsGrid from "./AvailableSlotsGrid.vue";

defineProps({
	slots: {
		type: Array,
		default: () => [],
	},
	selectedSlotId: {
		type: String,
		default: "",
	},
	isLoading: {
		type: Boolean,
		default: false,
	},
	error: {
		type: String,
		default: "",
	},
});

defineEmits(["select-slot"]);
</script>
