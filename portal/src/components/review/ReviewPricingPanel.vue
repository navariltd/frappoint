<template>
	<div class="glass-card rounded-xl p-6 space-y-4">
		<h3 class="text-headline-sm font-headline-sm text-on-surface">Pricing Summary</h3>

		<div class="space-y-2.5">
			<!-- Subtotal -->
			<div class="flex items-center justify-between text-body-md text-on-surface">
				<span class="text-on-surface-variant">Subtotal</span>
				<span>{{ fmt(pricing.subtotal) }}</span>
			</div>

			<!-- Appointment discounts -->
			<div
				v-if="pricing.appointmentDiscountTotal > 0"
				class="flex items-center justify-between text-body-md"
			>
				<span class="text-on-surface-variant flex items-center gap-1.5">
					<span class="material-symbols-outlined text-secondary text-[16px]"
						>local_offer</span
					>
					Appointment discounts
				</span>
				<span class="text-secondary font-medium"
					>–{{ fmt(pricing.appointmentDiscountTotal) }}</span
				>
			</div>

			<!-- Booking coupon discount -->
			<div
				v-if="pricing.bookingDiscountAmount > 0"
				class="flex items-center justify-between text-body-md"
			>
				<span class="text-on-surface-variant flex items-center gap-1.5">
					<span class="material-symbols-outlined text-secondary text-[16px]"
						>confirmation_number</span
					>
					Coupon discount
				</span>
				<span class="text-secondary font-medium"
					>–{{ fmt(pricing.bookingDiscountAmount) }}</span
				>
			</div>

			<!-- Divider -->
			<div class="border-t border-outline-variant/20 pt-3 mt-1">
				<div class="flex items-center justify-between">
					<span class="text-body-md font-semibold text-on-surface">Total Payable</span>
					<span class="text-headline-sm font-headline-sm text-primary">
						{{ fmt(pricing.finalAmount) }}
					</span>
				</div>

				<!-- Savings callout -->
				<p
					v-if="totalDiscount > 0"
					class="text-label-sm text-secondary mt-1.5 flex items-center gap-1"
				>
					<span class="material-symbols-outlined text-[14px]">savings</span>
					You save {{ fmt(totalDiscount) }} on this booking
				</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { formatCurrency } from "@/utils";
import type { ReviewPricingSummary } from "@/stores/bookingReview.store";

const props = defineProps<{
	pricing: ReviewPricingSummary;
	currency: string;
}>();

const totalDiscount = computed(
	() =>
		Number(props.pricing.appointmentDiscountTotal || 0) +
		Number(props.pricing.bookingDiscountAmount || 0)
);

function fmt(amount: number) {
	return formatCurrency(Number(amount || 0), props.currency);
}
</script>
