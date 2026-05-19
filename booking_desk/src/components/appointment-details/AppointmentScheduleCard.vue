<template>
	<section
		class="rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-wider text-outline">
					Schedule
				</p>
				<h2 class="mt-1 text-lg font-semibold text-on-surface">
					{{ appointment.appointmentDate || "No date set" }}
				</h2>
			</div>
			<span class="material-symbols-outlined text-primary">schedule</span>
		</div>
		<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
			<div class="rounded-xl bg-surface-container px-3 py-3">
				<p class="text-[11px] uppercase tracking-wider text-outline">Scheduled</p>
				<p class="mt-1 font-semibold text-on-surface">
					{{ appointment.startTime || "-" }} - {{ appointment.endTime || "-" }}
				</p>
			</div>
			<div class="rounded-xl bg-surface-container px-3 py-3">
				<p class="text-[11px] uppercase tracking-wider text-outline">Actual</p>
				<p class="mt-1 font-semibold text-on-surface">
					{{ appointment.actualStartTime || "-" }} -
					{{ appointment.actualEndTime || "-" }}
				</p>
			</div>
			<div class="rounded-xl bg-surface-container px-3 py-3 sm:col-span-2">
				<p class="text-[11px] uppercase tracking-wider text-outline">Status</p>
				<p class="mt-1 font-semibold text-on-surface">
					{{ appointment.status || "Open" }} ·
					{{ appointment.paymentStatus || "Unpaid" }}
				</p>
			</div>
		</div>
		<div class="flex flex-wrap gap-2">
			<button
				class="px-3 py-2 rounded-full border border-outline-variant text-on-surface-variant hover:bg-surface-container-high"
				type="button"
				@click="$emit('reschedule')"
			>
				Reschedule
			</button>
			<button
				class="px-3 py-2 rounded-full border border-outline-variant text-on-surface-variant hover:bg-surface-container-high"
				type="button"
				@click="$emit('reassign-provider')"
			>
				Reassign provider
			</button>
		</div>
	</section>
</template>

<script setup>
defineProps({
	appointment: { type: Object, required: true },
});

defineEmits(["reschedule", "reassign-provider"]);
</script>
