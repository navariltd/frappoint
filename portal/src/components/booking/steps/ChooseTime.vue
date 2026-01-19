<template>
	<div class="w-full lg:w-full flex flex-col lg:flex-row">
		<!-- LEFT COLUMN: Calendar  -->
		<div
			class="w-full lg:w-5/12 p-6 md:p-8 border-b lg:border-b-0 lg:border-r border-slate-100 bg-white flex flex-col"
		>
			<DatePicker
				:model-value="selectedDate"
				@update:model-value="$emit('update:selectedDate', $event)"
				:allowed-dates="availableDates"
				variant="subtle"
				:disabled="false"
			/>
		</div>

		<!-- RIGHT COLUMN: Time Slots  -->
		<div
			v-if="selectedDate"
			class="w-full lg:w-7/12 p-6 md:p-8 flex flex-col bg-surface-light relative"
		>
			<!-- provider  -->
			<div class="mb-8 border-collapse">
				<FormControl
					type="select"
					:options="providerOptions"
					:model-value="selectedProvider"
					@update:model-value="$emit('update:selectedProvider', $event)"
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
						{{ formatSelectedDate(selectedDate) }}
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
						@click="$emit('selectSlot', slot)"
						:class="
							selectedSlot === slot
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
						@click="$emit('selectSlot', slot)"
						:class="
							selectedSlot === slot
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
								{{ serviceType }}
							</p>
							<p v-if="selectedSlot" class="text-xs text-slate-500">
								{{ servicePrice }} . {{ formatTime(selectedSlot.start_time) }}
							</p>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Button, DatePicker, FeatherIcon, FormControl } from "frappe-ui";
import { computed } from "vue";

const props = defineProps({
	selectedDate: [String, null],
	selectedSlot: Object,
	selectedProvider: [String, null],
	availableDates: Array,
	availableSlots: Array,
	serviceType: String,
	servicePrice: String,
});

const emit = defineEmits(["update:selectedDate", "update:selectedProvider", "selectSlot"]);

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
	if (!props.selectedProvider) {
		return props.availableSlots;
	}

	return props.availableSlots.filter((slot) => slot.provider === props.selectedProvider);
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

	const jsDate = new Date(`${date}T00:00:00`);

	if (isNaN(jsDate.getTime())) return "";

	return jsDate.toLocaleDateString("en-US", {
		weekday: "long",
		month: "long",
		day: "numeric",
	});
}
</script>
