<template>
	<div v-if="open" class="fixed inset-0 z-40">
		<div class="absolute inset-0 bg-black/20" @click="$emit('close')"></div>
		<aside
			class="absolute right-0 top-0 h-full w-full max-w-[420px] bg-white shadow-xl border-l border-outline-variant flex flex-col"
		>
			<div class="p-4 border-b border-outline-variant/40 flex items-center justify-between">
				<h3 class="text-[14px] font-semibold text-on-surface">Appointment Details</h3>
				<button
					class="p-1 rounded hover:bg-surface-container-high"
					@click="$emit('close')"
				>
					<span class="material-symbols-outlined text-[18px]">close</span>
				</button>
			</div>
			<div v-if="event" class="p-4 overflow-y-auto flex-1 space-y-4">
				<div class="flex items-start justify-between gap-2">
					<div>
						<p class="text-[11px] text-on-surface-variant">
							#{{ event.appointmentId }}
						</p>
						<p class="text-[16px] font-semibold text-on-surface">
							{{ event.customerName }}
						</p>
					</div>
					<CalendarStatusBadge :status="event.status" />
				</div>
				<div class="grid grid-cols-2 gap-2 text-[12px]">
					<div
						class="rounded-md border border-outline-variant/40 p-2 bg-surface-container-lowest"
					>
						<p class="text-on-surface-variant">Service</p>
						<p class="font-semibold text-on-surface">{{ event.service }}</p>
					</div>
					<div
						class="rounded-md border border-outline-variant/40 p-2 bg-surface-container-lowest"
					>
						<p class="text-on-surface-variant">Provider</p>
						<p class="font-semibold text-on-surface">{{ event.provider }}</p>
					</div>
					<div
						class="rounded-md border border-outline-variant/40 p-2 bg-surface-container-lowest"
					>
						<p class="text-on-surface-variant">Time</p>
						<p class="font-semibold text-on-surface">
							{{ event.startTime }} - {{ event.endTime }}
						</p>
					</div>
					<div
						class="rounded-md border border-outline-variant/40 p-2 bg-surface-container-lowest"
					>
						<p class="text-on-surface-variant">Booking</p>
						<p class="font-semibold text-on-surface">{{ event.bookingId || "N/A" }}</p>
					</div>
				</div>
				<div class="space-y-2 pt-2">
					<button
						class="w-full rounded-lg px-3 py-2 bg-primary text-on-primary text-[12px] font-semibold hover:opacity-90"
						@click="$emit('openFull', event)"
					>
						Open Full Appointment
					</button>
					<div class="grid grid-cols-2 gap-2">
						<button
							v-for="action in actions"
							:key="action.value"
							:disabled="busy"
							class="rounded-lg px-2 py-2 border border-outline-variant text-[11px] font-semibold text-on-surface-variant hover:bg-surface-container-high disabled:opacity-50"
							@click="$emit('action', action.value)"
						>
							{{ action.label }}
						</button>
					</div>
				</div>
			</div>
		</aside>
	</div>
</template>

<script setup>
import CalendarStatusBadge from "@/components/calendar/CalendarStatusBadge.vue";

const actions = [
	{ value: "check_in", label: "Check In" },
	{ value: "start", label: "Start" },
	{ value: "pause", label: "Pause" },
	{ value: "resume", label: "Resume" },
	{ value: "complete", label: "Complete" },
	{ value: "reschedule", label: "Reschedule" },
	{ value: "cancel", label: "Cancel" },
];

defineProps({
	open: { type: Boolean, default: false },
	event: { type: Object, default: null },
	busy: { type: Boolean, default: false },
});

defineEmits(["close", "openFull", "action"]);
</script>
