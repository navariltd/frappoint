<template>
	<div class="w-full flex flex-col bg-surface-light relative">
		<div>
			<div class="flex items-center justify-between mb-4">
				<h1 class="text-lg font-bold text-slate-900">Available Time Slots</h1>
			</div>

			<div v-if="loading">
				<TimeSlotSkeleton :count="12" />
			</div>

			<div v-else>
				<div
					v-if="hasSlots"
					class="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-2 overflow-y-auto max-h-[320px] time-slot-scroll pr-2"
				>
					<template v-if="morningSlots.length">
						<div class="col-span-full mt-2 mb-1">
							<p>Morning</p>
						</div>

						<Button
							v-for="slot in morningSlots"
							:key="slot.id"
							@click="$emit('select', slot.id)"
							:disabled="isSlotDisabled(slot)"
							:class="buttonStateClass(slot)"
							class="py-4 px-4 rounded-lg border border-slate-200 text-slate-700 hover:border-primary hover:text-primary hover:bg-[#E2F0F9] transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:border-slate-200 disabled:hover:text-slate-700 disabled:hover:bg-white"
						>
							{{ formatTime(slot.startTime) }}
						</Button>
					</template>

					<template v-if="afternoonSlots.length">
						<div class="col-span-full mt-2 mb-1">
							<p>Afternoon</p>
						</div>

						<Button
							v-for="slot in afternoonSlots"
							:key="slot.id"
							@click="$emit('select', slot.id)"
							:disabled="isSlotDisabled(slot)"
							:class="buttonStateClass(slot)"
							class="py-4 px-4 rounded-lg border border-slate-200 text-slate-700 hover:border-primary hover:text-primary hover:bg-[#E2F0F9] transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:border-slate-200 disabled:hover:text-slate-700 disabled:hover:bg-white"
						>
							{{ formatTime(slot.startTime) }}
						</Button>
					</template>
				</div>

				<div
					v-else
					class="flex flex-col items-center justify-center text-center bg-white rounded-lg border border-slate-200 p-8"
					aria-live="polite"
				>
					<FeatherIcon name="clock" class="w-10 h-10 text-slate-400 mb-2" />
					<p class="text-slate-800 font-medium">No available slots at the moment.</p>
					<p class="text-slate-500 text-sm mt-1">Please choose another date.</p>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, FeatherIcon } from "frappe-ui";
import { computed } from "vue";
import type { AvailableSlot } from "@/services/bookingWorkflow.service";
import TimeSlotSkeleton from "./TimeSlotSkeleton.vue";

const props = defineProps<{
	slots: AvailableSlot[];
	selectedSlotId?: string;
	loading: boolean;
}>();

defineEmits<{
	select: [slotId: string];
}>();

const hasSlots = computed(() => props.slots.length > 0);

const morningSlots = computed(() =>
	props.slots.filter((slot) => Number(slot.startTime.split(":")[0]) < 12)
);

const afternoonSlots = computed(() =>
	props.slots.filter((slot) => Number(slot.startTime.split(":")[0]) >= 12)
);

function isSlotDisabled(slot: AvailableSlot) {
	return slot.availability === "unavailable" || slot.slotIds.length === 0;
}

function buttonStateClass(slot: AvailableSlot) {
	if (isSlotDisabled(slot)) {
		return "!bg-white !text-slate-400 !border-slate-200";
	}
	if (props.selectedSlotId === slot.id) {
		return "!bg-primary !text-white !border-primary";
	}
	if (slot.availability === "partial") {
		return "!bg-amber-50 !text-amber-800 !border-amber-200";
	}
	return "border hover-bg-primary/10";
}

function formatTime(time: string) {
	if (!time) return "";
	const [hours, minutes] = time.split(":");
	const date = new Date();
	date.setHours(Number(hours), Number(minutes));
	return date.toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
	});
}
</script>
