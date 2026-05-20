<template>
	<section
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
					Service
				</p>
				<h2 class="mt-1 text-base font-semibold tracking-tight text-on-surface">
					{{ appointment.appointmentType || "Service" }}
				</h2>
			</div>
			<span class="material-symbols-outlined text-primary">spa</span>
		</div>
		<div
			class="rounded-md border border-outline-variant/30 divide-y divide-outline-variant/20 text-sm"
		>
			<div class="flex items-start justify-between gap-3 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Duration</p>
				<p class="font-medium text-on-surface">{{ appointment.duration || 0 }} min</p>
			</div>
			<div class="flex items-start justify-between gap-3 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Provider</p>
				<p class="font-medium text-on-surface text-right max-w-[65%] break-words">
					{{ appointment.provider || "Unassigned" }}
				</p>
			</div>
			<div class="flex items-start justify-between gap-3 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Time window</p>
				<p class="font-medium text-on-surface text-right">
					{{ appointment.startTime || "-" }} - {{ appointment.endTime || "-" }}
				</p>
			</div>
		</div>
		<div
			v-if="appointment.details"
			class="rounded-md border border-outline-variant/30 bg-surface px-3 py-2.5 text-sm text-on-surface-variant"
		>
			{{ appointment.details }}
		</div>
	</section>
</template>

<script setup>
defineProps({
	appointment: { type: Object, required: true },
});
</script>
