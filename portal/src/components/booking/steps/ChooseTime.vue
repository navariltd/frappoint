<template>
	<div class="w-full lg:w-full flex flex-col lg:flex-row">
		<!-- LEFT COLUMN: Calendar  -->
		<div
			class="w-full lg:w-6/12 p-2 md:p-8 border-b lg:border-b-0 lg:border-r border-slate-100 bg-white flex flex-col"
		>
			<!-- Loading skeleton for calendar -->
			<div v-if="datesLoading" class="animate-pulse">
				<div class="flex items-center justify-between mb-6">
					<div class="h-6 w-24 bg-slate-200 rounded"></div>
					<div class="h-6 w-24 bg-slate-200 rounded"></div>
				</div>
				<div class="grid grid-cols-7 gap-2 mb-4">
					<div v-for="i in 7" :key="i" class="h-10 bg-slate-100 rounded"></div>
				</div>
				<div class="grid grid-cols-7 gap-2">
					<div v-for="i in 35" :key="i" class="h-12 bg-slate-100 rounded"></div>
				</div>
			</div>

			<!-- Empty state when no dates available -->
			<div
				v-else-if="!datesLoading && formattedAllowedDates.length === 0"
				class="flex-1 flex flex-col items-center justify-center text-center p-8"
			>
				<div class="mb-4 p-4 bg-slate-100 rounded-full">
					<FeatherIcon name="calendar-x" class="w-12 h-12 text-slate-400" />
				</div>
				<h3 class="text-lg font-bold text-slate-900 mb-2">No Dates Available</h3>
				<p class="text-slate-600 text-sm max-w-xs">
					There are currently no available dates for this service. Please check back
					later or contact us for assistance.
				</p>
			</div>

			<!-- Actual calendar -->
			<VueDatePicker
				v-else
				:model-value="date"
				@update:model-value="$emit('update:date', $event)"
				:allowed-dates="formattedAllowedDates"
				:start-date="firstAvailableDate"
				inline
				auto-apply
				:transitions="true"
				:time-config="{ enableTimePicker: false }"
				class="vue-datepicker-custom"
			/>
		</div>

		<!-- RIGHT COLUMN: Time Slots  -->
		<div class="w-full lg:w-7/12 p-6 md:p-8 flex flex-col bg-surface-light relative">
			<!-- Empty state when no date selected -->
			<div
				v-if="!date"
				class="flex-1 flex flex-col items-center justify-center text-center p-8"
			>
				<div class="mb-4 p-4 bg-white rounded-full shadow-sm">
					<FeatherIcon name="calendar" class="w-12 h-12 text-teal-600" />
				</div>
				<h3 class="text-lg font-bold text-gray-900 mb-2">Select a Date</h3>
				<p class="text-gray-600 text-sm max-w-xs">
					Please select a date from the calendar to view available time slots for your
					appointment.
				</p>
			</div>

			<!-- Time slots content when date is selected -->
			<template v-else>
				<!-- provider  -->
				<div class="mb-8 border-collapse">
					<!-- Loading skeleton for provider dropdown -->
					<div v-if="slotsLoading" class="animate-pulse">
						<div class="h-4 w-48 bg-slate-200 rounded mb-2"></div>
						<div class="h-12 w-full bg-slate-100 rounded"></div>
					</div>

					<!-- Actual dropdown -->
					<FormControl
						v-else
						type="select"
						:options="providerOptions"
						:model-value="provider"
						@update:model-value="$emit('update:provider', $event)"
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
							{{ formatSelectedDate(date) }}
						</h1>
					</div>

					<!-- Loading slots skeleton -->
					<div v-if="slotsLoading">
						<TimeSlotSkeleton :count="12" />
					</div>

					<!-- Time slots grid -->
					<div v-else>
						<!-- Slots available -->
						<div
							v-if="hasSlots"
							class="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-8 overflow-y-auto max-h-[320px] time-slot-scroll pr-2"
						>
							<!-- Morning section -->
							<template v-if="morningSlots.length">
								<div class="col-span-full mt-2 mb-1">
									<p>Morning</p>
								</div>

								<Button
									v-for="slot in morningSlots"
									:key="slot.start_time + slot.provider"
									@click="$emit('update:slot', slot)"
									:class="
										isSlotSelected(slot)
											? '!bg-primary !text-white'
											: 'border hover-bg-primary/10'
									"
									class="py-4 px-4 rounded-lg border border-slate-200 text-slate-700 hover:border-primary hover:text-primary hover:bg-[#E2F0F9] transition-all text-sm font-medium"
								>
									{{ formatTime(slot.start_time) }}
								</Button>
							</template>

							<!-- Afternoon section -->
							<template v-if="afternoonSlots.length">
								<div class="col-span-full mt-2 mb-1">
									<p>Afternoon</p>
								</div>

								<Button
									v-for="slot in afternoonSlots"
									:key="slot.start_time + slot.provider"
									@click="$emit('update:slot', slot)"
									:class="
										isSlotSelected(slot)
											? '!bg-primary !text-white'
											: 'broder hover-bg-primary/10'
									"
									class="py-4 px-4 rounded-lg border border-slate-200 text-slate-700 hover:border-primary hover:text-primary hover:bg-[#E2F0F9] transition-all text-sm font-medium"
								>
									{{ formatTime(slot.start_time) }}
								</Button>
							</template>
						</div>

						<!-- Empty state when no slots -->
						<div
							v-else
							class="flex flex-col items-center justify-center text-center bg-white rounded-lg border border-slate-200 p-8"
							aria-live="polite"
						>
							<FeatherIcon name="clock" class="w-10 h-10 text-slate-400 mb-2" />
							<p class="text-slate-800 font-medium">
								No available slots at the moment.
							</p>
							<p class="text-slate-500 text-sm mt-1">
								Please choose another service.
							</p>
						</div>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { Button, FeatherIcon, FormControl } from "frappe-ui";
import { VueDatePicker } from "@vuepic/vue-datepicker";
import "@vuepic/vue-datepicker/dist/main.css";
import { computed } from "vue";
import TimeSlotSkeleton from "../TimeSlotSkeleton.vue";

const props = defineProps({
	date: [String, Object],
	slot: Object,
	provider: String,
	availableDates: Array,
	availableSlots: Array,
	canProceed: Boolean,
	datesLoading: Boolean,
	slotsLoading: Boolean,
});

defineEmits(["continue", "update:date", "update:slot", "update:provider"]);

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
	if (!props.provider) {
		return props.availableSlots;
	}

	return props.availableSlots.filter((slot) => slot.provider === props.provider);
});

const hasSlots = computed(() => visibleSlots.value && visibleSlots.value.length > 0);

// Filter out past time slots if the selected date is today
const availableSlots = computed(() => {
	if (!props.date) return visibleSlots.value;

	// Get selected date
	const selectedDate =
		props.date instanceof Date ? props.date : new Date(`${props.date}T00:00:00`);

	// Get current date and time
	const now = new Date();
	const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
	const selectedDateOnly = new Date(
		selectedDate.getFullYear(),
		selectedDate.getMonth(),
		selectedDate.getDate()
	);

	// If selected date is not today, return all slots
	if (selectedDateOnly.getTime() !== today.getTime()) {
		return visibleSlots.value;
	}

	// If it's today, filter out past time slots
	const currentHours = now.getHours();
	const currentMinutes = now.getMinutes();

	return visibleSlots.value.filter((slot) => {
		const [slotHours, slotMinutes] = slot.start_time.split(":").map(Number);

		// Compare time
		if (slotHours > currentHours) return true;
		if (slotHours === currentHours && slotMinutes > currentMinutes) return true;

		return false;
	});
});

const morningSlots = computed(() =>
	availableSlots.value.filter((s) => Number(s.start_time.split(":")[0]) < 12)
);

const afternoonSlots = computed(() =>
	availableSlots.value.filter((s) => Number(s.start_time.split(":")[0]) >= 12)
);

const isSlotSelected = (s) => {
	return props.slot?.start_time === s.start_time && props.slot?.provider === s.provider;
};

const firstAvailableDate = computed(() => {
	if (!formattedAllowedDates.value || formattedAllowedDates.value.length === 0) {
		return new Date();
	}
	const sortedDates = [...formattedAllowedDates.value].sort((a, b) => a - b);
	return sortedDates[0];
});

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
