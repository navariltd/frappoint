<template>
	<div class="glass-card rounded-xl p-6 space-y-4">
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
				class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-label-sm font-semibold"
				:class="statusClass"
			>
				<span class="w-1.5 h-1.5 rounded-full bg-current"></span>
				{{ booking.status }}
			</span>
		</div>

		<div class="grid grid-cols-2 gap-3 pt-2">
			<div class="rounded-lg bg-surface-container p-3">
				<p
					class="text-label-xs uppercase tracking-wider text-on-surface-variant font-semibold"
				>
					Grand Total
				</p>
				<p class="text-body-lg font-semibold text-on-surface mt-1">
					{{ formattedTotal }}
				</p>
			</div>
			<div class="rounded-lg bg-surface-container p-3">
				<p
					class="text-label-xs uppercase tracking-wider text-on-surface-variant font-semibold"
				>
					Outstanding
				</p>
				<p class="text-body-lg font-semibold text-primary mt-1">
					{{ formattedOutstanding }}
				</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { formatCurrency } from "@/utils";
import type { CheckoutBookingSummary } from "@/services/checkout.service";

const props = defineProps<{
	booking: CheckoutBookingSummary;
}>();

const formattedTotal = computed(() =>
	formatCurrency(Number(props.booking.grandTotal || 0), props.booking.currency)
);
const formattedOutstanding = computed(() =>
	formatCurrency(Number(props.booking.outstandingAmount || 0), props.booking.currency)
);

const statusClass = computed(() => {
	const status = (props.booking.status || "").toLowerCase();
	if (status === "confirmed" || status === "paid")
		return "bg-secondary-container text-on-secondary-container";
	if (status === "draft" || status === "pending")
		return "bg-tertiary-container text-on-tertiary-container";
	if (status === "cancelled") return "bg-error-container text-on-error-container";
	return "bg-surface-container-high text-on-surface-variant";
});
</script>
