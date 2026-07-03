<template>
	<div class="space-y-4">
		<div v-if="isLoading" class="p-8 text-center">
			<div
				class="inline-block w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin"
			></div>
			<p class="text-body-sm text-on-surface-variant mt-2">Loading available slots...</p>
		</div>

		<div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
			<button
				v-for="slot in availableSlots"
				:key="slot.id"
				class="p-4 rounded-lg border transition-all text-center"
				:class="[
					selectedSlotId === slot.id
						? 'bg-primary border-primary text-on-primary'
						: 'border-outline-variant/30 hover:border-primary/50 bg-surface-container text-on-surface hover:bg-surface-container-high',
				]"
				@click="$emit('select', slot.id)"
			>
				<p class="text-label-lg font-semibold">{{ slot.startTime }}</p>
				<p class="text-label-sm opacity-70">{{ slot.endTime }}</p>
				<p v-if="slot.providerSummary" class="text-label-xs opacity-60 mt-2">
					{{ slot.providerSummary }}
				</p>
			</button>
		</div>

		<div
			v-if="availableSlots.length === 0 && !isLoading"
			class="p-8 text-center rounded-lg bg-surface-container"
		>
			<span class="material-symbols-outlined text-[40px] text-on-surface-variant block mb-2">
				schedule
			</span>
			<p class="text-body-md text-on-surface-variant">No available slots for this date</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { AvailableSlot } from "@/services/bookingWorkflow.service";

const props = defineProps<{
	slots?: AvailableSlot[];
	selectedSlotId?: string;
	isLoading: boolean;
}>();

defineEmits<{
	select: [slotId: string];
}>();

const availableSlots = computed(() => props.slots || []);
</script>
