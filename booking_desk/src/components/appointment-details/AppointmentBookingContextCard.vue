<template>
	<section
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
					Booking context
				</p>
				<h2 class="mt-1 text-base font-semibold tracking-tight text-on-surface">
					{{ booking.bookingId || "No booking" }}
				</h2>
			</div>
			<span class="material-symbols-outlined text-primary">bookmark</span>
		</div>
		<div
			class="rounded-md border border-outline-variant/30 divide-y divide-outline-variant/20 text-sm"
		>
			<div class="flex items-start justify-between gap-3 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Booking status</p>
				<p class="font-medium text-on-surface">{{ booking.status || "Draft" }}</p>
			</div>
			<div class="flex items-start justify-between gap-3 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Appointments</p>
				<p class="font-medium text-on-surface">{{ booking.appointmentCount || 0 }}</p>
			</div>
			<div class="flex items-start justify-between gap-3 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Customer</p>
				<p class="font-medium text-on-surface text-right max-w-[65%] break-words">
					{{ booking.customerName || appointment.customerName || "-" }}
				</p>
			</div>
		</div>
		<button
			class="w-full px-4 py-2 rounded-md border border-outline-variant/70 text-on-surface-variant hover:bg-surface-container-high hover:border-outline transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/30"
			type="button"
			@click="$emit('open-booking')"
		>
			Open booking workspace
		</button>
	</section>
</template>

<script setup>
defineProps({
	booking: { type: Object, default: () => ({}) },
	appointment: { type: Object, default: () => ({}) },
});

defineEmits(["open-booking"]);
</script>
