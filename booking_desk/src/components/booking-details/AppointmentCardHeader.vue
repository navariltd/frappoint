<template>
	<div class="flex items-start justify-between gap-3 mt-0.5">
		<div class="min-w-0">
			<h4 class="text-[16px] font-semibold text-on-surface truncate">
				{{ appointment.fullName }}
			</h4>
			<p class="text-[13px] text-on-surface-variant truncate">
				{{ appointment.serviceType }}
			</p>
		</div>
		<div class="flex flex-col items-end gap-1 shrink-0">
			<BookingStatusBadge :status="appointment.status" />
			<PaymentStatusBadge :status="appointment.paymentStatus" />
		</div>
	</div>
</template>

<script setup>
import BookingStatusBadge from "@/components/booking-details/BookingStatusBadge.vue";
import PaymentStatusBadge from "@/components/booking-details/PaymentStatusBadge.vue";

defineProps({ appointment: { type: Object, required: true } });
</script>
