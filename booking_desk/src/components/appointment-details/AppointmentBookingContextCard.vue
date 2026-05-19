<template>
	<section
		class="rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-wider text-outline">
					Booking context
				</p>
				<h2 class="mt-1 text-lg font-semibold text-on-surface">
					{{ booking.bookingId || "No booking" }}
				</h2>
			</div>
			<span class="material-symbols-outlined text-primary">bookmark</span>
		</div>
		<div class="grid grid-cols-2 gap-3 text-sm">
			<div class="rounded-xl bg-surface-container px-3 py-3">
				<p class="text-[11px] uppercase tracking-wider text-outline">Booking status</p>
				<p class="mt-1 font-semibold text-on-surface">{{ booking.status || "Draft" }}</p>
			</div>
			<div class="rounded-xl bg-surface-container px-3 py-3">
				<p class="text-[11px] uppercase tracking-wider text-outline">Appointments</p>
				<p class="mt-1 font-semibold text-on-surface">
					{{ booking.appointmentCount || 0 }}
				</p>
			</div>
			<div class="rounded-xl bg-surface-container px-3 py-3 col-span-2">
				<p class="text-[11px] uppercase tracking-wider text-outline">Customer</p>
				<p class="mt-1 font-semibold text-on-surface">
					{{ booking.customerName || appointment.customerName || "-" }}
				</p>
			</div>
		</div>
		<button
			class="w-full px-4 py-2 rounded-full border border-outline-variant text-on-surface-variant hover:bg-surface-container-high"
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
