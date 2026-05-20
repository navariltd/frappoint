<template>
	<section
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 shadow-sm min-h-[12rem]"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<h3 class="text-sm font-semibold text-on-surface">Appointment Details Preview</h3>
				<p class="text-[11px] text-on-surface-variant mt-1">
					Click an appointment in timeline to inspect details.
				</p>
			</div>
		</div>

		<div
			v-if="!appointment"
			class="mt-4 rounded-md border border-dashed border-outline-variant/60 bg-surface px-4 py-6 text-center text-[12px] text-on-surface-variant"
		>
			No appointment selected.
		</div>

		<div v-else class="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-[12px]">
			<div class="rounded-md border border-outline-variant/30 bg-surface px-3 py-2.5">
				<p class="text-on-surface-variant">Guest</p>
				<p class="font-semibold text-on-surface truncate">{{ appointment.guestName }}</p>
			</div>
			<div class="rounded-md border border-outline-variant/30 bg-surface px-3 py-2.5">
				<p class="text-on-surface-variant">Service</p>
				<p class="font-semibold text-on-surface truncate">{{ appointment.service }}</p>
			</div>
			<div class="rounded-md border border-outline-variant/30 bg-surface px-3 py-2.5">
				<p class="text-on-surface-variant">Provider</p>
				<p class="font-semibold text-on-surface truncate">{{ providerName }}</p>
			</div>
			<div class="rounded-md border border-outline-variant/30 bg-surface px-3 py-2.5">
				<p class="text-on-surface-variant">Status</p>
				<p class="font-semibold text-on-surface capitalize">
					{{ appointment.status || "Open" }}
				</p>
			</div>
			<div class="rounded-md border border-outline-variant/30 bg-surface px-3 py-2.5">
				<p class="text-on-surface-variant">Date</p>
				<p class="font-semibold text-on-surface">
					{{ appointment.date || appointment.appointmentDate || "-" }}
				</p>
			</div>
			<div class="rounded-md border border-outline-variant/30 bg-surface px-3 py-2.5">
				<p class="text-on-surface-variant">Start Time</p>
				<p class="font-semibold text-on-surface">{{ appointment.startTime || "-" }}</p>
			</div>
			<div class="rounded-md border border-outline-variant/30 bg-surface px-3 py-2.5">
				<p class="text-on-surface-variant">Duration</p>
				<p class="font-semibold text-on-surface">{{ appointment.duration || 0 }}h</p>
			</div>
			<div class="rounded-md border border-outline-variant/30 bg-surface px-3 py-2.5">
				<p class="text-on-surface-variant">Appointment</p>
				<p class="font-semibold text-on-surface">{{ appointment.id || "-" }}</p>
			</div>
		</div>
	</section>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	appointment: { type: Object, default: null },
	providers: { type: Array, default: () => [] },
});

const providerName = computed(() => {
	if (!props.appointment) {
		return "-";
	}
	const provider = props.providers.find((item) => item.id === props.appointment.providerId);
	return provider?.name || "Unassigned";
});
</script>
