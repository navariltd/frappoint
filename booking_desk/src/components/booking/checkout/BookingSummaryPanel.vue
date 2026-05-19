<template>
	<section
		class="rounded-2xl border border-outline-variant bg-surface-container-low p-4 h-full overflow-y-auto"
	>
		<div class="flex items-center justify-between mb-3">
			<h3 class="text-[15px] font-semibold text-on-surface">Booking Summary</h3>
			<span class="text-[11px] text-on-surface-variant">{{ booking.status }}</span>
		</div>

		<div class="mb-4 rounded-xl border border-outline-variant bg-surface p-3">
			<p class="text-[13px] font-semibold text-on-surface">
				{{ booking.fullName || "Walk-in Customer" }}
			</p>
			<p class="text-[12px] text-on-surface-variant">{{ booking.mobileNo || "No phone" }}</p>
		</div>

		<div class="space-y-2">
			<div
				v-for="appointment in booking.appointments"
				:key="appointment.name"
				class="rounded-xl border border-outline-variant bg-surface p-3"
			>
				<div class="flex items-start justify-between gap-2">
					<div>
						<p class="text-[12px] font-semibold text-on-surface">
							{{ appointment.fullName }}
						</p>
						<p class="text-[12px] text-on-surface-variant">
							{{ appointment.serviceType }}
						</p>
					</div>
					<p class="text-[12px] font-semibold text-primary">
						{{ booking.currency }}
						{{ Number(appointment.totalAmount || 0).toFixed(2) }}
					</p>
				</div>
				<p class="text-[11px] text-on-surface-variant mt-1">
					{{ appointment.date }} • {{ appointment.startTime }} -
					{{ appointment.endTime }}
				</p>
				<p class="text-[11px] text-on-surface-variant">
					{{ appointment.paymentStatus || "Unpaid" }} • Outstanding:
					{{ booking.currency }}
					{{ Number(appointment.outstandingAmount || 0).toFixed(2) }}
				</p>
			</div>
		</div>
	</section>
</template>

<script setup>
defineProps({
	booking: {
		type: Object,
		required: true,
	},
});
</script>
