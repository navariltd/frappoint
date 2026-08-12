<template>
	<header
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 md:p-5 shadow-sm"
	>
		<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
			<div class="space-y-3">
				<div class="flex flex-wrap items-center gap-2 text-[12px] text-outline">
					<span class="font-semibold text-on-surface"
						>#{{ appointment.appointmentId }}</span
					>
					<span
						v-if="appointment.bookingId"
						class="h-1 w-1 rounded-full bg-outline"
					></span>
					<span v-if="appointment.bookingId">Booking {{ appointment.bookingId }}</span>
					<span
						v-if="appointment.appointmentDate"
						class="h-1 w-1 rounded-full bg-outline"
					></span>
					<span>{{ appointment.appointmentDate }}</span>
				</div>
				<div>
					<h1 class="text-xl md:text-2xl font-semibold tracking-tight text-on-surface">
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
				<div class="flex flex-wrap gap-1.5">
					<span
						v-if="appointment.isCouple"
						class="px-2.5 py-1 rounded-md bg-primary-container text-on-primary-container text-[10px] font-semibold uppercase tracking-[0.08em]"
					>
						{{
							appointment.isPrimaryInCouple ? "Couple · Primary" : "Couple · Partner"
						}}
					</span>
					<span
						class="px-2.5 py-1 rounded-md bg-primary-container text-on-primary-container text-[10px] font-semibold uppercase tracking-[0.08em]"
					>
						{{ appointment.status || "Open" }}
					</span>
					<span
						class="px-2.5 py-1 rounded-md bg-surface-container-high text-on-surface-variant text-[10px] font-semibold uppercase tracking-[0.08em]"
					>
						{{ appointment.paymentStatus || "Unpaid" }}
					</span>
					<span
						class="px-2.5 py-1 rounded-md bg-surface-container-high text-on-surface-variant text-[10px] font-semibold uppercase tracking-[0.08em]"
					>
						{{ appointment.currency }}
						{{ Number(financialSummary.totalAmount || 0).toFixed(2) }}
					</span>
				</div>
				<p
					v-if="appointment.coupleAppointmentId"
					class="text-[11px] font-medium text-primary"
				>
					Linked couple appointment: {{ appointment.coupleAppointmentId }}
				</p>
			</div>

			<div class="flex flex-wrap gap-2 lg:justify-end lg:max-w-[560px]">
				<button
					class="px-3.5 py-2 rounded-md border border-outline-variant/70 text-on-surface-variant hover:bg-surface-container-high hover:border-outline transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/30"
					type="button"
					@click="$emit('back')"
				>
					Back
				</button>
				<button
					class="px-3.5 py-2 rounded-md border border-primary/70 text-primary hover:bg-primary/10 hover:border-primary transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40 disabled:opacity-45 disabled:cursor-not-allowed"
					type="button"
					:disabled="busy || !actions.canCheckIn"
					@click="$emit('check-in')"
				>
					Check in
				</button>
				<button
					class="px-3.5 py-2 rounded-md border border-primary bg-primary text-on-primary hover:bg-primary-dark transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40 disabled:opacity-45 disabled:cursor-not-allowed"
					type="button"
					:disabled="busy || !actions.canStart"
					@click="$emit('start')"
				>
					Start
				</button>
				<button
					class="px-3.5 py-2 rounded-md border border-warning/70 text-warning hover:bg-warning/10 hover:border-warning transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-warning/40 disabled:opacity-45 disabled:cursor-not-allowed"
					type="button"
					:disabled="busy || !actions.canPause"
					@click="$emit('pause')"
				>
					Pause
				</button>
				<button
					class="px-3.5 py-2 rounded-md border border-outline-variant/70 text-on-surface-variant hover:bg-surface-container-high hover:border-outline transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/30 disabled:opacity-45 disabled:cursor-not-allowed"
					type="button"
					:disabled="busy || !actions.canResume"
					@click="$emit('resume')"
				>
					Resume
				</button>
				<button
					class="px-3.5 py-2 rounded-md border border-success/60 text-success hover:bg-success/10 hover:border-success transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success/30 disabled:opacity-45 disabled:cursor-not-allowed"
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

defineEmits(["back", "check-in", "start", "pause", "resume", "complete"]);
</script>
