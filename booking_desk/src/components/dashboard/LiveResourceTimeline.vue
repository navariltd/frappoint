<template>
	<section class="space-y-3">
		<div
			v-if="error"
			class="rounded-md border border-error/40 bg-error-container/20 px-3 py-2 text-[12px] text-on-surface flex items-center justify-between"
		>
			<span>{{ error }}</span>
			<button class="text-primary font-semibold" @click="$emit('retry')">Retry</button>
		</div>
		<div v-if="loading" class="text-[12px] text-on-surface-variant px-1">
			Loading dashboard data...
		</div>
		<div :class="panelHeightClass">
			<ResourceTimeline
				title="Live Resource Timeline"
				class="h-full"
				:providers="providers"
				:appointments="appointments"
				:selectedDateValue="selectedDate"
				:defaultView="view"
				:statuses="statuses"
				@appointments-updated="$emit('appointments-updated', $event)"
				@date-changed="$emit('date-changed', $event)"
				@view-changed="$emit('view-changed', $event)"
				@appointment-selected="$emit('appointment-selected', $event)"
			/>
		</div>
	</section>
</template>

<script setup>
import ResourceTimeline from "@/components/dashboard/ResourceTimeline.vue";

defineProps({
	providers: { type: Array, default: () => [] },
	appointments: { type: Array, default: () => [] },
	selectedDate: { type: String, default: "" },
	view: { type: String, default: "day" },
	statuses: { type: Array, default: () => [] },
	loading: { type: Boolean, default: false },
	error: { type: String, default: "" },
	panelHeightClass: { type: String, default: "h-[34rem]" },
});

defineEmits([
	"appointments-updated",
	"date-changed",
	"view-changed",
	"retry",
	"appointment-selected",
]);
</script>
