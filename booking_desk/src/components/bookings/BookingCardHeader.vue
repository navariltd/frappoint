<template>
	<div class="flex justify-between items-start">
		<div>
			<span class="text-[13px] text-outline font-semibold">#{{ booking.bookingId }}</span>
			<h3 class="text-[16px] font-semibold mt-0.5 text-on-surface">
				{{ booking.customerName }}
			</h3>
		</div>
		<div class="flex flex-col items-end gap-2">
			<BookingStatusBadge :status="booking.status" />
			<PaymentStatusBadge :status="booking.paymentStatus" />
		</div>
	</div>
</template>

<script setup>
import BookingStatusBadge from "@/components/bookings/BookingStatusBadge.vue";
import PaymentStatusBadge from "@/components/bookings/PaymentStatusBadge.vue";

defineProps({ booking: { type: Object, required: true } });
</script>
