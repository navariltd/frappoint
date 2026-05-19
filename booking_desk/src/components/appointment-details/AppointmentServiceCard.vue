<template>
	<section
		class="rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-wider text-outline">
					Service
				</p>
				<h2 class="mt-1 text-lg font-semibold text-on-surface">
					{{ appointment.appointmentType || "Service" }}
				</h2>
			</div>
			<span class="material-symbols-outlined text-primary">spa</span>
		</div>
		<div class="grid grid-cols-2 gap-3 text-sm">
			<div class="rounded-xl bg-surface-container px-3 py-3">
				<p class="text-[11px] uppercase tracking-wider text-outline">Duration</p>
				<p class="mt-1 font-semibold text-on-surface">
					{{ appointment.duration || 0 }} min
				</p>
			</div>
			<div class="rounded-xl bg-surface-container px-3 py-3">
				<p class="text-[11px] uppercase tracking-wider text-outline">Provider</p>
				<p class="mt-1 font-semibold text-on-surface">
					{{ appointment.provider || "Unassigned" }}
				</p>
			</div>
			<div class="rounded-xl bg-surface-container px-3 py-3 col-span-2">
				<p class="text-[11px] uppercase tracking-wider text-outline">Time window</p>
				<p class="mt-1 font-semibold text-on-surface">
					{{ appointment.startTime || "-" }} - {{ appointment.endTime || "-" }}
				</p>
			</div>
		</div>
		<div
			v-if="appointment.details"
			class="rounded-xl border border-outline-variant/30 bg-surface p-3 text-sm text-on-surface-variant"
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
