<template>
	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
		<SlotCard
			v-for="slot in slots"
			:key="slot.id"
			:slot="slot"
			:selected="selectedSlotId === slot.id || pendingSlotId === slot.id"
			:pending="pendingSlotId === slot.id"
			:disabled="disabled"
			@select="$emit('select-slot', $event)"
		/>
	</div>
</template>

<script setup>
import SlotCard from "./SlotCard.vue";

defineProps({
	slots: {
		type: Array,
		default: () => [],
	},
	selectedSlotId: {
		type: String,
		default: "",
	},
	pendingSlotId: {
		type: String,
		default: "",
	},
	disabled: {
		type: Boolean,
		default: false,
	},
});

defineEmits(["select-slot"]);
</script>
