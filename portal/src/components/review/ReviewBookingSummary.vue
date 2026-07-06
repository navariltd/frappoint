<template>
	<div class="glass-card rounded-xl p-6 space-y-4">
		<!-- Header row -->
		<div class="flex items-start justify-between gap-4">
			<div>
				<p
					class="text-label-sm uppercase tracking-widest text-on-surface-variant font-semibold mb-1"
				>
					Service Booking
				</p>
				<h2 class="text-headline-sm font-headline-sm text-on-surface">
					{{ booking.name }}
				</h2>
				<p class="text-body-sm text-on-surface-variant mt-1">
					{{ booking.fullName || booking.customer }}
					<span v-if="booking.email"> · {{ booking.email }}</span>
				</p>
			</div>
			<span
				class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-label-sm font-semibold shrink-0"
				:class="statusClass"
			>
				<span class="w-1.5 h-1.5 rounded-full bg-current"></span>
				{{ booking.status }}
			</span>
		</div>

		<!-- Stats -->
		<div class="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-1">
			<div class="rounded-lg bg-surface-container p-3">
				<p
					class="text-label-xs uppercase tracking-wider text-on-surface-variant font-semibold"
				>
					Appointments
				</p>
				<p class="text-body-lg font-semibold text-on-surface mt-1">
					{{ booking.appointmentCount }}
				</p>
			</div>
			<div class="rounded-lg bg-surface-container p-3">
				<p
					class="text-label-xs uppercase tracking-wider text-on-surface-variant font-semibold"
				>
					Guests
				</p>
				<p class="text-body-lg font-semibold text-on-surface mt-1">
					{{ booking.totalGuests }}
				</p>
			</div>
			<div class="rounded-lg bg-surface-container p-3 col-span-2 sm:col-span-1">
				<p
					class="text-label-xs uppercase tracking-wider text-on-surface-variant font-semibold"
				>
					Currency
				</p>
				<p class="text-body-lg font-semibold text-on-surface mt-1">
					{{ booking.currency }}
				</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ReviewBookingInfo } from "@/stores/bookingReview.store";

const props = defineProps<{
	booking: ReviewBookingInfo;
}>();

const statusClass = computed(() => {
	const s = (props.booking.status || "").toLowerCase();
	if (s === "confirmed" || s === "paid")
		return "bg-secondary-container text-on-secondary-container";
	if (s === "draft" || s === "pending")
		return "bg-tertiary-container text-on-tertiary-container";
	if (s === "cancelled") return "bg-error-container text-on-error-container";
	return "bg-surface-container-high text-on-surface-variant";
});
</script>
