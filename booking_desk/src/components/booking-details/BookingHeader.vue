<template>
	<div class="flex flex-col md:flex-row md:items-end justify-between gap-4">
		<div>
			<div class="flex items-center gap-3 mb-1 text-[12px] text-outline">
				<span class="font-semibold text-on-surface">#{{ booking.bookingId }}</span>
				<span class="h-1.5 w-1.5 rounded-full bg-outline-variant"></span>
				<span>{{ booking.bookingDate || "Created date unavailable" }}</span>
			</div>
			<h2 class="text-[22px] md:text-[24px] font-semibold text-on-surface">
				{{ booking.customerName }}
			</h2>
			<div class="flex flex-wrap gap-2 mt-3">
				<BookingStatusBadge :status="booking.status" />
				<PaymentStatusBadge :status="booking.paymentStatus" />
				<span
					class="px-3 py-1 rounded-full bg-surface-container text-[11px] font-semibold text-on-surface-variant"
					>{{ metrics.appointmentCount }} Appointments</span
				>
				<span
					class="px-3 py-1 rounded-full bg-surface-container text-[11px] font-semibold text-on-surface-variant"
					>{{ metrics.totalGuests }} Guests</span
				>
			</div>
		</div>
		<div
			class="flex gap-3 bg-surface-container-low p-4 rounded-2xl border border-outline-variant"
		>
			<div class="text-center px-4 border-r border-outline-variant/60">
				<p class="text-outline text-[11px] uppercase tracking-wider">Date</p>
				<p class="text-on-surface font-semibold">{{ booking.bookingDate || "-" }}</p>
			</div>
			<div class="text-center px-4 border-r border-outline-variant/60">
				<p class="text-outline text-[11px] uppercase tracking-wider">Guests</p>
				<p class="text-on-surface font-semibold">{{ metrics.totalGuests }}</p>
			</div>
			<div class="text-center px-4">
				<p class="text-outline text-[11px] uppercase tracking-wider">Appointments</p>
				<p class="text-on-surface font-semibold">{{ metrics.appointmentCount }}</p>
			</div>
		</div>
	</div>
</template>

<script setup>
import BookingStatusBadge from "@/components/booking-details/BookingStatusBadge.vue";
import PaymentStatusBadge from "@/components/booking-details/PaymentStatusBadge.vue";

defineProps({
	booking: { type: Object, required: true },
	metrics: { type: Object, required: true },
});
</script>
