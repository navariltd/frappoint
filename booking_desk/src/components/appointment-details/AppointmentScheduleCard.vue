<template>
	<section
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
					Schedule
				</p>
				<h2 class="mt-1 text-base font-semibold tracking-tight text-on-surface">
					{{ appointment.appointmentDate || "No date set" }}
				</h2>
			</div>
			<span class="material-symbols-outlined text-primary">schedule</span>
		</div>
		<div
			class="rounded-md border border-outline-variant/30 divide-y divide-outline-variant/20 text-sm"
		>
			<div class="flex items-start justify-between gap-3 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Scheduled</p>
				<p class="font-medium text-on-surface text-right">
					{{ appointment.startTime || "-" }} - {{ appointment.endTime || "-" }}
				</p>
			</div>
			<div class="flex items-start justify-between gap-3 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Actual</p>
				<p class="font-medium text-on-surface text-right">
					{{ appointment.actualStartTime || "-" }} -
					{{ appointment.actualEndTime || "-" }}
				</p>
			</div>
			<div class="flex items-start justify-between gap-3 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Status</p>
				<p class="font-medium text-on-surface text-right">
					{{ appointment.status || "Open" }} ·
					{{ appointment.paymentStatus || "Unpaid" }}
				</p>
			</div>
		</div>
		<div class="flex flex-wrap gap-2 pt-1">
			<button
				v-if="actions.canReschedule"
				class="px-3 py-2 rounded-md border border-outline-variant/70 text-on-surface-variant hover:bg-surface-container-high hover:border-outline transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
				type="button"
				@click="$emit('reschedule')"
			>
				Reschedule
			</button>
			<button
				v-if="actions.canReassignProvider"
				class="px-3 py-2 rounded-md border border-outline-variant/70 text-on-surface-variant hover:bg-surface-container-high hover:border-outline transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
				type="button"
				@click="$emit('reassign-provider')"
			>
				Change Service Provider
			</button>
		</div>
	</section>
</template>

<script setup>
defineProps({
	appointment: { type: Object, required: true },
	actions: { type: Object, default: () => ({}) },
});

defineEmits(["reschedule", "reassign-provider"]);
</script>
