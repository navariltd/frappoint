<template>
	<div>
		<div v-if="loading" class="animate-pulse">
			<div class="flex items-center justify-between mb-6">
				<div class="h-6 w-24 bg-slate-200 rounded"></div>
				<div class="h-6 w-24 bg-slate-200 rounded"></div>
			</div>
			<div class="grid grid-cols-7 gap-2 mb-4">
				<div v-for="i in 7" :key="i" class="h-10 bg-slate-100 rounded"></div>
			</div>
			<div class="grid grid-cols-7 gap-2">
				<div v-for="i in 35" :key="`cell-${i}`" class="h-12 bg-slate-100 rounded"></div>
			</div>
		</div>

		<div
			v-else-if="!loading && allowedDates.length === 0"
			class="flex flex-col items-center justify-center text-center bg-white rounded-lg border border-slate-200 p-8 min-h-[320px]"
		>
			<div class="mb-4 p-4 bg-slate-100 rounded-full">
				<span class="material-symbols-outlined text-[40px] text-slate-400"
					>calendar_month</span
				>
			</div>
			<h3 class="text-lg font-bold text-slate-900 mb-2">No Dates Available</h3>
			<p class="text-slate-600 text-sm max-w-xs">
				There are currently no available dates for this service. Please check back later.
			</p>
		</div>

		<VueDatePicker
			v-else
			:model-value="pickerValue"
			@update:model-value="onSelectDate"
			:allowed-dates="allowedDates"
			:start-date="firstAvailableDate"
			inline
			auto-apply
			:transitions="true"
			:time-config="{ enableTimePicker: false }"
			class="vue-datepicker-custom"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { VueDatePicker } from "@vuepic/vue-datepicker";
import "@vuepic/vue-datepicker/dist/main.css";
import type { AvailableDate } from "@/services/bookingWorkflow.service";

const props = defineProps<{
	dates: AvailableDate[];
	selectedDate?: string;
	loading: boolean;
}>();

const emit = defineEmits<{
	select: [date: string];
}>();

const allowedDates = computed(() =>
	(props.dates || [])
		.map((item) => {
			const [year, month, day] = item.date.split("-").map(Number);
			if (!year || !month || !day) return null;
			return new Date(year, month - 1, day);
		})
		.filter((item): item is Date => Boolean(item))
);

const pickerValue = computed(() => {
	if (!props.selectedDate) return null;
	const [year, month, day] = props.selectedDate.split("-").map(Number);
	if (!year || !month || !day) return null;
	return new Date(year, month - 1, day);
});

const firstAvailableDate = computed(() => {
	if (!allowedDates.value.length) return new Date();
	return [...allowedDates.value].sort((a, b) => a.getTime() - b.getTime())[0];
});

function onSelectDate(value: Date | Date[] | string | null) {
	if (!value || Array.isArray(value)) return;
	const date = typeof value === "string" ? new Date(value) : value;
	if (Number.isNaN(date.getTime())) return;
	const formatted = [
		date.getFullYear(),
		String(date.getMonth() + 1).padStart(2, "0"),
		String(date.getDate()).padStart(2, "0"),
	].join("-");
	emit("select", formatted);
}
</script>

<style scoped>
.vue-datepicker-custom {
	--dp-font-family: inherit;
	--dp-border-radius: 12px;
	--dp-cell-border-radius: 8px;
	--dp-primary-color: rgb(var(--color-primary));
	--dp-primary-text-color: #ffffff;
	--dp-hover-color: rgb(var(--color-primary-container));
	--dp-hover-text-color: rgb(var(--color-on-primary-container));
	--dp-cell-size: 44px;
	--dp-button-height: 35px;
}

:deep(.dp__main) {
	width: 100%;
}

:deep(.dp__menu) {
	border: 0;
	box-shadow: none;
	background: transparent;
}

:deep(.dp__calendar) {
	padding: 0;
}

:deep(.dp__calendar_header) {
	font-weight: 600;
	color: #475569;
}

:deep(.dp__calendar_header_item) {
	padding: 0.5rem;
	font-size: 0.875rem;
}

:deep(.dp__calendar_item) {
	padding: 0.2rem;
}

:deep(.dp__cell_inner) {
	height: 100%;
	width: 100%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-weight: 500;
}

:deep(.dp__cell_disabled) {
	color: #cbd5e1;
	cursor: not-allowed;
}

:deep(.dp__cell_disabled .dp__cell_inner) {
	background: transparent;
}

:deep(.dp__today) {
	border: 2px solid rgb(var(--color-primary));
}

:deep(.dp__active_date) {
	background: rgb(var(--color-primary)) !important;
	color: white !important;
}

:deep(.dp__cell_inner:hover) {
	background: rgb(var(--color-primary-container));
	color: rgb(var(--color-on-primary-container));
}

:deep(.dp__arrow_top),
:deep(.dp__arrow_bottom),
:deep(.dp__calendar_header_separator) {
	display: none;
}

:deep(.dp__month_year_select) {
	color: rgb(var(--color-primary));
}

:deep(.dp__month_year_select:hover) {
	background: rgb(var(--color-primary-container));
	color: rgb(var(--color-on-primary-container));
}
</style>
