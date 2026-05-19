<template>
	<header
		class="rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-5 md:p-6 shadow-sm"
	>
		<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
			<div class="space-y-3">
				<div class="flex flex-wrap items-center gap-2 text-[12px] text-outline">
					<span class="font-semibold text-on-surface"
						>#{{ appointment.appointmentId }}</span
					>
					<span
						v-if="appointment.bookingId"
						class="h-1.5 w-1.5 rounded-full bg-outline-variant"
					></span>
					<span v-if="appointment.bookingId">Booking {{ appointment.bookingId }}</span>
					<span
						v-if="appointment.appointmentDate"
						class="h-1.5 w-1.5 rounded-full bg-outline-variant"
					></span>
					<span>{{ appointment.appointmentDate }}</span>
				</div>
				<div>
					<h1 class="text-2xl md:text-3xl font-semibold text-on-surface">
						{{
							appointment.fullName ||
							appointment.customerName ||
							"Appointment details"
						}}
					</h1>
					<p class="mt-1 text-sm text-on-surface-variant">
						{{ appointment.appointmentType || "Service appointment" }}
						<span v-if="appointment.provider"> · {{ appointment.provider }}</span>
					</p>
				</div>
				<div class="flex flex-wrap gap-2">
					<span
						class="px-3 py-1 rounded-full bg-primary-container text-on-primary-container text-[11px] font-semibold uppercase tracking-wider"
					>
						{{ appointment.status || "Open" }}
					</span>
					<span
						class="px-3 py-1 rounded-full bg-surface-container-high text-on-surface-variant text-[11px] font-semibold uppercase tracking-wider"
					>
						{{ appointment.paymentStatus || "Unpaid" }}
					</span>
					<span
						class="px-3 py-1 rounded-full bg-surface-container-high text-on-surface-variant text-[11px] font-semibold uppercase tracking-wider"
					>
						{{ appointment.currency }}
						{{ Number(financialSummary.totalAmount || 0).toFixed(2) }}
					</span>
				</div>
			</div>

			<div class="flex flex-wrap gap-2 lg:justify-end">
				<button
					class="px-4 py-2 rounded-full border border-outline-variant text-on-surface-variant hover:bg-surface-container-high"
					type="button"
					@click="$emit('back')"
				>
					Back
				</button>
				<button
					class="px-4 py-2 rounded-full border border-primary text-primary hover:bg-primary/5 disabled:opacity-60"
					type="button"
					:disabled="busy || !actions.canCheckIn"
					@click="$emit('check-in')"
				>
					Check in
				</button>
				<button
					class="px-4 py-2 rounded-full bg-primary text-on-primary disabled:opacity-60"
					type="button"
					:disabled="busy || !actions.canStart"
					@click="$emit('start')"
				>
					Start
				</button>
				<button
					class="px-4 py-2 rounded-full border border-outline-variant text-on-surface-variant hover:bg-surface-container-high disabled:opacity-60"
					type="button"
					:disabled="busy || !actions.canComplete"
					@click="$emit('complete')"
				>
					Complete
				</button>
			</div>
		</div>
	</header>
</template>

<script setup>
defineProps({
	appointment: { type: Object, required: true },
	financialSummary: { type: Object, required: true },
	actions: { type: Object, default: () => ({}) },
	busy: { type: Boolean, default: false },
});

defineEmits(["back", "check-in", "start", "complete"]);
</script>
