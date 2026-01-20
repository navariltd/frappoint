<template>
	<div class="w-full lg:w-full flex flex-col lg:flex-row">
		<!-- LEFT COLUMN: Calendar  -->
		<div
			class="w-full lg:w-5/12 p-6 md:p-8 border-b lg:border-b-0 lg:border-r border-slate-100 bg-white flex flex-col"
		>
			<VueDatePicker
				:model-value="booking.draft.date"
				@update:model-value="booking.setDate($event)"
				:allowed-dates="formattedAllowedDates"
				:enable-time-picker="false"
				inline
				auto-apply
				:transitions="true"
				class="vue-datepicker-custom"
			/>
		</div>

		<!-- RIGHT COLUMN: Time Slots  -->
		<div
			v-if="booking.draft.date"
			class="w-full lg:w-7/12 p-6 md:p-8 flex flex-col bg-surface-light relative"
		>
			<!-- provider  -->
			<div class="mb-8 border-collapse">
				<FormControl
					type="select"
					:options="providerOptions"
					:model-value="booking.draft.provider"
					@update:model-value="booking.setProvider($event)"
					size="xl"
					variant="subtle"
					placeholder="Any Available Staff"
					:disabled="false"
					label="Select Staff Member (Optional)"
					class="w-full appearance-none bg-white text-slate-900 px-4 pr-10 focus:!outline-none focus:!ring-2 focus:!ring-primary/50 focus:!border-primary transition-shadow cursor-pointer"
				/>
			</div>

			<!-- Date and slots  -->
			<div>
				<div class="flex items-center justify-between mb-4">
					<h1 class="text-lg font-bold text-slate-900">
						{{ formatSelectedDate(booking.draft.date) }}
					</h1>
				</div>

				<div
					class="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-8 overflow-y-auto max-h-[320px] time-slot-scroll pr-2"
				>
					<div class="col-span-full mt-2 mb-1">
						<p>Morning</p>
					</div>

					<Button
						v-for="slot in morningSlots"
						:key="slot.start_time + slot.provider"
						@click="booking.setSlot(slot)"
						:class="
							booking.draft.slot === slot
								? '!bg-primary !text-white'
								: 'border hover-bg-primary/10'
						"
						class="py-4 px-4 rounded-lg border border-slate-200 text-slate-700 hover:border-primary hover:text-primary hover:bg-[#E2F0F9] transition-all text-sm font-medium"
					>
						{{ formatTime(slot.start_time) }}
					</Button>

					<div class="col-span-full mt-2 mb-1">
						<p>Afternoon</p>
					</div>

					<Button
						v-for="slot in afternoonSlots"
						:key="slot.start_time + slot.provider"
						@click="booking.setSlot(slot)"
						:class="
							booking.draft.slot === slot
								? '!bg-primary !text-white'
								: 'broder hover-bg-primary/10'
						"
						class="py-4 px-4 rounded-lg border border-slate-200 text-slate-700 hover:border-primary hover:text-primary hover:bg-[#E2F0F9] transition-all text-sm font-medium"
					>
						{{ formatTime(slot.start_time) }}
					</Button>
				</div>
			</div>

			<!-- Footer Action Area  -->
			<div class="mt-auto pt-6 border-t border-slate-100">
				<div
					class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
				>
					<!-- Summary  -->
					<div class="flex items-start gap-3">
						<div
							class="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-slate-500"
						>
							<FeatherIcon class="h-4" name="clock" />
						</div>
						<div>
							<p class="text-sm font-bold text-slate-900">
								{{ booking.draft.serviceType }}
							</p>
							<p v-if="booking.draft.slot" class="text-xs text-slate-500">
								{{ formatCurrency(booking.draft.price, booking.draft.currency) }} .
								{{ formatTime(booking.draft.slot.start_time) }}
							</p>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Button, FeatherIcon, FormControl } from "frappe-ui";
import { VueDatePicker } from "@vuepic/vue-datepicker";
import "@vuepic/vue-datepicker/dist/main.css";
import { computed } from "vue";
import { useBookingStore } from "@/stores/bookingStore";
import { formatCurrency } from "@/utils";

const props = defineProps({
	availableDates: Array,
	availableSlots: Array,
});

const booking = useBookingStore();

// Convert available dates to Date objects for VueDatepicker
const formattedAllowedDates = computed(() => {
	if (!props.availableDates || !Array.isArray(props.availableDates)) return [];

	return props.availableDates
		.map((dateStr) => {
			const dateValue = typeof dateStr === "string" ? dateStr : dateStr?.date;
			if (!dateValue) return null;

			const [year, month, day] = dateValue.split("-");
			return new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
		})
		.filter((date) => date !== null);
});

const providerOptions = computed(() => {
	const map = new Map();

	for (const slot of props.availableSlots) {
		if (!map.has(slot.provider)) {
			map.set(slot.provider, {
				label: slot.provider_name,
				value: slot.provider,
			});
		}
	}

	return [{ label: "Any Available Staff", value: null }, ...Array.from(map.values())];
});

const visibleSlots = computed(() => {
	if (!booking.draft.provider) {
		return props.availableSlots;
	}

	return props.availableSlots.filter((slot) => slot.provider === booking.draft.provider);
});

const morningSlots = computed(() =>
	visibleSlots.value.filter((s) => Number(s.start_time.split(":")[0]) < 12)
);

const afternoonSlots = computed(() =>
	visibleSlots.value.filter((s) => Number(s.start_time.split(":")[0]) >= 12)
);

function formatTime(time) {
	if (!time) return "";

	const [h, m] = time.split(":");
	const date = new Date();
	date.setHours(h, m);
	return date.toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
	});
}

function formatSelectedDate(date) {
	if (!date) return "";

	// Handle Date object from VueDatepicker
	let jsDate;
	if (date instanceof Date) {
		jsDate = date;
	} else {
		jsDate = new Date(`${date}T00:00:00`);
	}

	if (isNaN(jsDate.getTime())) return "";

	return jsDate.toLocaleDateString("en-US", {
		weekday: "long",
		month: "long",
		day: "numeric",
	});
}
</script>

<style scoped>
.vue-datepicker-custom {
	--dp-font-family: inherit;
	--dp-border-radius: 12px;
	--dp-cell-border-radius: 8px;
	--dp-primary-color: #2c7677;
	--dp-primary-text-color: #ffffff;
	--dp-hover-color: #d1e7e7;
	--dp-hover-text-color: #2c7677;
	--dp-cell-size: 48px;
	--dp-button-height: 35px;
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
	padding: 0.25rem;
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
	border: 2px solid #2c7677;
}

:deep(.dp__active_date) {
	background: #2c7677 !important;
	color: white !important;
}

:deep(.dp__cell_inner:hover) {
	background: #d1e7e7;
	color: #2c7677;
}

:deep(.dp__arrow_top),
:deep(.dp__arrow_bottom),
:deep(.dp__calendar_header_separator) {
	display: none;
}

:deep(.dp__month_year_select) {
	color: #2c7677;
}

:deep(.dp__month_year_select:hover) {
	background: #d1e7e7;
	color: #2c7677;
}
</style>
