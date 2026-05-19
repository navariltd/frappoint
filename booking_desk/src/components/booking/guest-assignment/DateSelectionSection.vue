<template>
	<div class="space-y-2 border-t border-outline-variant pt-3">
		<div class="flex items-center justify-between">
			<p class="text-[11px] font-semibold uppercase tracking-wide text-on-surface">
				2. Select Date
			</p>
			<button type="button" class="text-[11px] text-primary" @click="$emit('load-dates')">
				Refresh
			</button>
		</div>
		<p v-if="isLoading" class="text-[11px] text-on-surface-variant">
			Loading available dates...
		</p>
		<p v-else-if="error" class="text-[11px] text-error">{{ error }}</p>
		<p v-else-if="!dates.length" class="text-[11px] text-on-surface-variant">
			No available dates for this service duration.
		</p>
		<AvailableDatesList
			v-else
			:dates="dates"
			:selectedDate="selectedDate"
			@select="$emit('select-date', $event)"
		/>
	</div>
</template>

<script setup>
import AvailableDatesList from "./AvailableDatesList.vue";

defineProps({
	dates: {
		type: Array,
		default: () => [],
	},
	selectedDate: {
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

defineEmits(["load-dates", "select-date"]);
</script>
