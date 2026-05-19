<template>
	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
		<SlotCard
			v-for="slot in slots"
			:key="slot.id"
			:slot="slot"
			:selected="selectedSlotId === slot.id"
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
});

defineEmits(["select-slot"]);
</script>
