<template>
	<button
		type="button"
		class="w-full rounded-md border border-primary/50 bg-primary px-2 py-1 text-left text-on-primary-container transition-colors hover:bg-primary-container hover:text-on-primary hover:shadow-lg"
		@click="$emit('select', event)"
	>
		<div class="flex items-start justify-between gap-2">
			<p class="text-[11px] font-semibold text-on-surface truncate">{{ event.service }}</p>
			<CalendarStatusBadge :status="event.status" />
		</div>
		<p class="text-[10px] text-on-surface-variant truncate mt-1">{{ event.customerName }}</p>
		<p class="text-[10px] text-on-surface-variant truncate">
			{{ event.startTime }} - {{ event.endTime }}
		</p>
	</button>
</template>

<script setup>
import CalendarStatusBadge from "@/components/calendar/CalendarStatusBadge.vue";

defineProps({
	event: { type: Object, required: true },
});

defineEmits(["select"]);
</script>
