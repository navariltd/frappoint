<template>
	<div class="grid grid-cols-2 gap-2 text-[12px] mt-3">
		<div
			class="rounded-lg border border-outline-variant/60 bg-surface-container-low px-3 py-2"
		>
			<p class="text-on-surface-variant">Date</p>
			<p class="font-medium text-on-surface">{{ appointment.date || "-" }}</p>
		</div>
		<div
			class="rounded-lg border border-outline-variant/60 bg-surface-container-low px-3 py-2"
		>
			<p class="text-on-surface-variant">Time</p>
			<p class="font-medium text-on-surface">
				{{ appointment.startTime || "--:--" }} - {{ appointment.endTime || "--:--" }}
			</p>
		</div>
		<div
			class="rounded-lg border border-outline-variant/60 bg-surface-container-low px-3 py-2"
		>
			<p class="text-on-surface-variant">Provider</p>
			<p class="font-medium text-on-surface">{{ appointment.provider || "Unassigned" }}</p>
		</div>
		<div
			class="rounded-lg border border-outline-variant/60 bg-surface-container-low px-3 py-2"
		>
			<p class="text-on-surface-variant">Outstanding</p>
			<p class="font-medium text-primary">
				{{ currency }} {{ Number(appointment.outstandingAmount || 0).toFixed(2) }}
			</p>
		</div>
	</div>
</template>

<script setup>
defineProps({
	appointment: { type: Object, required: true },
	currency: { type: String, default: "KES" },
});
</script>
