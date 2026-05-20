<template>
	<div class="space-y-4">
		<div v-if="loading" class="p-8 text-center">
			<div
				class="inline-block w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin"
			></div>
			<p class="text-body-sm text-on-surface-variant mt-2">Loading available dates...</p>
		</div>

		<div v-else-if="dates.length" class="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
			<button
				v-for="item in dates"
				:key="item.date"
				class="p-3 rounded-lg border transition-all"
				:class="
					selectedDate === item.date
						? 'bg-primary border-primary text-on-primary'
						: 'border-outline-variant/30 hover:border-primary/50 bg-surface-container text-on-surface hover:bg-surface-container-high'
				"
				@click="$emit('select', item.date)"
			>
				<p class="text-label-md font-semibold">{{ day(item.date) }}</p>
				<p class="text-label-sm opacity-70">{{ month(item.date) }}</p>
			</button>
		</div>

		<div v-else class="p-8 text-center rounded-lg bg-surface-container">
			<span class="material-symbols-outlined text-[40px] text-on-surface-variant block mb-2"
				>calendar_month</span
			>
			<p class="text-body-md text-on-surface-variant">No available dates for this service</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AvailableDate } from "@/services/bookingWorkflow.service";

defineProps<{
	dates: AvailableDate[];
	selectedDate?: string;
	loading: boolean;
}>();

defineEmits<{
	select: [date: string];
}>();

function day(date: string) {
	return new Date(`${date}T00:00:00`).getDate().toString();
}

function month(date: string) {
	return new Date(`${date}T00:00:00`).toLocaleDateString("en-US", { month: "short" });
}
</script>
