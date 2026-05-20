<template>
	<div class="space-y-4">
		<div v-if="isLoading" class="p-8 text-center">
			<div
				class="inline-block w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin"
			></div>
			<p class="text-body-sm text-on-surface-variant mt-2">Loading available dates...</p>
		</div>

		<div v-else class="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
			<button
				v-for="item in availableDates"
				:key="item.date"
				class="p-3 rounded-lg border transition-all"
				:class="[
					selectedDate === item.date
						? 'bg-primary border-primary text-on-primary'
						: 'border-outline-variant/30 hover:border-primary/50 bg-surface-container text-on-surface hover:bg-surface-container-high',
				]"
				@click="$emit('select', item.date)"
			>
				<p class="text-label-md font-semibold">{{ formatDateDay(item.date) }}</p>
				<p class="text-label-sm opacity-70">{{ formatDateMonth(item.date) }}</p>
			</button>
		</div>

		<div
			v-if="availableDates.length === 0 && !isLoading"
			class="p-8 text-center rounded-lg bg-surface-container"
		>
			<span class="material-symbols-outlined text-[40px] text-on-surface-variant block mb-2">
				calendar_month
			</span>
			<p class="text-body-md text-on-surface-variant">No available dates for this service</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { AvailableDate } from "@/services/bookingWorkflow.service";

const props = defineProps<{
	dates?: AvailableDate[];
	selectedDate?: string;
	isLoading: boolean;
}>();

defineEmits<{
	select: [date: string];
}>();

const availableDates = computed(() => props.dates || []);

function formatDateDay(date: string): string {
	const d = new Date(`${date}T00:00:00`);
	return d.getDate().toString();
}

function formatDateMonth(date: string): string {
	const d = new Date(`${date}T00:00:00`);
	return d.toLocaleDateString("en-US", { month: "short" });
}
</script>
