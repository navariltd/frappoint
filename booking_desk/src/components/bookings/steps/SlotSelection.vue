<template>
	<div class="w-full lg:w-full flex flex-col lg:flex-row bg-white rounded-3xl overflow-hidden">
		<div
			class="w-full lg:w-6/12 p-2 md:p-8 border-b lg:border-b-0 lg:border-r border-slate-100 flex flex-col"
		>
			<div v-if="datesLoading" class="animate-pulse space-y-4">
				<div class="h-6 w-32 bg-slate-100 rounded"></div>
				<div class="h-64 bg-slate-50 rounded-2xl"></div>
			</div>

			<div
				v-else-if="!datesLoading && formattedAllowedDates.length === 0"
				class="flex-1 flex flex-col items-center justify-center text-center p-8"
			>
				<div class="mb-4 p-4 bg-slate-100 rounded-full">
					<FeatherIcon name="x-circle" class="w-10 h-10 text-slate-400" />
				</div>
				<h3 class="text-lg font-bold text-slate-900 mb-2">No Dates Available</h3>
				<p class="text-slate-500 text-sm">Check back later for new availability.</p>
			</div>

			<VueDatePicker
				v-else
				:model-value="date"
				@update:model-value="handleDateSelection"
				:allowed-dates="formattedAllowedDates"
				:start-date="firstAvailableDate"
				inline
				auto-apply
				:enable-time-picker="false"
				class="vue-datepicker-custom"
			/>
		</div>

		<div class="w-full lg:w-7/12 p-6 md:p-8 flex flex-col bg-slate-50/50 relative">
			<div
				v-if="!date"
				class="flex-1 flex flex-col items-center justify-center text-center p-8"
			>
				<div class="mb-4 p-4 bg-white rounded-full shadow-sm">
					<FeatherIcon name="calendar" class="w-10 h-10 text-primary" />
				</div>
				<h3 class="font-bold text-slate-900">Select a Date</h3>
				<p class="text-slate-500 text-sm">Choose a highlighted date on the left.</p>
			</div>

			<template v-else>
				<div class="mb-8">
					<label
						class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2"
						>Select Staff</label
					>
					<FormControl
						type="select"
						:options="providerOptions"
						:model-value="provider"
						@update:model-value="$emit('update:provider', $event)"
						variant="subtle"
						placeholder="Any Available Staff"
					/>
				</div>

				<div>
					<h1 class="text-lg font-bold text-slate-900 mb-6">
						{{ formatSelectedDate(date) }}
					</h1>

					<div v-if="slotsLoading">
						<TimeSlotSkeleton :count="9" />
					</div>

					<div v-else>
						<div v-if="hasSlots" class="space-y-6 max-h-[400px] overflow-y-auto pr-2">
							<div v-if="morningSlots.length">
								<p
									class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3"
								>
									Morning
								</p>
								<div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
									<Button
										v-for="slot in morningSlots"
										:key="slot.start_time + slot.provider"
										@click="$emit('update:slot', slot)"
										:class="
											isSlotSelected(slot)
												? '!bg-primary !text-white shadow-lg'
												: 'bg-white'
										"
										class="py-4 rounded-xl border border-slate-200 text-sm font-bold transition-all hover:border-primary"
									>
										{{ formatTime(slot.start_time) }}
									</Button>
								</div>
							</div>

							<div v-if="afternoonSlots.length">
								<p
									class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3"
								>
									Afternoon
								</p>
								<div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
									<Button
										v-for="slot in afternoonSlots"
										:key="slot.start_time + slot.provider"
										@click="$emit('update:slot', slot)"
										:class="
											isSlotSelected(slot)
												? '!bg-primary !text-white shadow-lg'
												: 'bg-white'
										"
										class="py-4 rounded-xl border border-slate-200 text-sm font-bold transition-all hover:border-primary"
									>
										{{ formatTime(slot.start_time) }}
									</Button>
								</div>
							</div>
						</div>

						<div
							v-else
							class="flex flex-col items-center justify-center text-center bg-white rounded-2xl border border-dashed border-slate-200 p-12"
						>
							<FeatherIcon name="clock" class="w-10 h-10 text-slate-300 mb-2" />
							<p class="text-slate-500 font-medium text-sm">
								No slots available for this staff member.
							</p>
						</div>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { Button, FeatherIcon, FormControl } from "frappe-ui";
import { VueDatePicker } from "@vuepic/vue-datepicker";
import "@vuepic/vue-datepicker/dist/main.css";
import TimeSlotSkeleton from "../TimeSlotSkeleton.vue";

const props = defineProps({
	date: [String, Object, Date],
	slot: Object,
	provider: String,
	availableDates: Array,
	availableSlots: Array,
	datesLoading: Boolean,
	slotsLoading: Boolean,
});

const emit = defineEmits(["update:date", "update:slot", "update:provider"]);

// IMPORTANT: Format JS Date to YYYY-MM-DD for backend consistency
function handleDateSelection(selected) {
	if (selected instanceof Date) {
		const y = selected.getFullYear();
		const m = String(selected.getMonth() + 1).padStart(2, "0");
		const d = String(selected.getDate()).padStart(2, "0");
		emit("update:date", `${y}-${m}-${d}`);
	} else {
		emit("update:date", selected);
	}
}

const formattedAllowedDates = computed(() => {
	if (!props.availableDates) return [];
	return props.availableDates.map((d) => new Date(d));
});

const providerOptions = computed(() => {
	const map = new Map();
	// Group unique providers from available slots
	(props.availableSlots || []).forEach((slot) => {
		if (!map.has(slot.provider)) {
			map.set(slot.provider, {
				label: slot.provider_name || slot.provider,
				value: slot.provider,
			});
		}
	});
	return [{ label: "Any Available Staff", value: null }, ...Array.from(map.values())];
});

// Filter slots by provider AND ensure they are in the future if today
const filteredSlots = computed(() => {
	let slots = props.availableSlots || [];

	if (props.provider) {
		slots = slots.filter((s) => s.provider === props.provider);
	}

	const now = new Date();
	const todayStr = now.toISOString().split("T")[0];

	if (props.date === todayStr) {
		const curH = now.getHours();
		const curM = now.getMinutes();
		return slots.filter((s) => {
			const [sh, sm] = s.start_time.split(":").map(Number);
			return sh > curH || (sh === curH && sm > curM);
		});
	}
	return slots;
});

const hasSlots = computed(() => filteredSlots.value.length > 0);

const morningSlots = computed(() =>
	filteredSlots.value.filter((s) => parseInt(s.start_time.split(":")[0]) < 12)
);

const afternoonSlots = computed(() =>
	filteredSlots.value.filter((s) => parseInt(s.start_time.split(":")[0]) >= 12)
);

const isSlotSelected = (s) => {
	return props.slot?.start_time === s.start_time && props.slot?.provider === s.provider;
};

const firstAvailableDate = computed(() => {
	if (!formattedAllowedDates.value.length) return new Date();
	return [...formattedAllowedDates.value].sort((a, b) => a - b)[0];
});

function formatTime(time) {
	if (!time) return "";
	const [h, m] = time.split(":");
	const date = new Date();
	date.setHours(h, m);
	return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatSelectedDate(dateStr) {
	if (!dateStr) return "";
	const jsDate = new Date(dateStr);
	return jsDate.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
}
</script>

<style scoped>
.vue-datepicker-custom {
	--dp-primary-color: #2c7677;
	--dp-border-radius: 20px;
}
:deep(.dp__input) {
	display: none;
}
:deep(.dp__outer_menu_wrap) {
	width: 100%;
	border: none;
}
</style>
