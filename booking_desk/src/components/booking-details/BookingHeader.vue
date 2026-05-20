<template>
	<header
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 md:p-5 shadow-sm"
	>
		<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
			<div class="space-y-3">
				<div class="flex flex-wrap items-center gap-2 text-[12px] text-outline">
					<span class="font-semibold text-on-surface">#{{ booking.bookingId }}</span>
					<span class="h-1 w-1 rounded-full bg-outline"></span>
					<span>{{ booking.bookingDate || "Created date unavailable" }}</span>
				</div>
				<div>
					<h1 class="text-xl md:text-2xl font-semibold tracking-tight text-on-surface">
						{{ booking.customerName }}
					</h1>
					<p class="mt-1 text-sm text-on-surface-variant">
						{{ metrics.appointmentCount }} appointment<span
							v-if="metrics.appointmentCount !== 1"
							>s</span
						>
						· {{ metrics.totalGuests }} guest<span v-if="metrics.totalGuests !== 1"
							>s</span
						>
					</p>
				</div>
				<div class="flex flex-wrap gap-1.5">
					<BookingStatusBadge :status="booking.status" />
					<PaymentStatusBadge :status="booking.paymentStatus" />
				</div>
			</div>
			<div class="space-y-1.5 text-sm">
				<div class="rounded-md border border-outline-variant/40 px-3 py-2.5">
					<p class="text-[11px] uppercase tracking-[0.08em] font-semibold text-outline">
						Total Value
					</p>
					<p class="mt-1 font-semibold text-primary">
						{{ booking.currency || "KES" }}
						{{ Number(booking.grandTotal || 0).toFixed(2) }}
					</p>
				</div>
				<div class="rounded-md border border-outline-variant/40 px-3 py-2.5">
					<p class="text-[11px] uppercase tracking-[0.08em] font-semibold text-outline">
						Total Duration
					</p>
					<p class="mt-1 font-semibold text-on-surface">{{ durationLabel }}</p>
				</div>
			</div>
		</div>
	</header>
</template>

<script setup>
import { computed } from "vue";
import BookingStatusBadge from "@/components/booking-details/BookingStatusBadge.vue";
import PaymentStatusBadge from "@/components/booking-details/PaymentStatusBadge.vue";

const props = defineProps({
	booking: { type: Object, required: true },
	metrics: { type: Object, required: true },
});

const durationLabel = computed(() => {
	const items = props.booking.items || props.booking.appointments || [];
	const minutes = items.reduce((sum, item) => sum + Number(item.duration || 0), 0);
	if (!minutes) return "--";
	return `${minutes}m`;
});
</script>
