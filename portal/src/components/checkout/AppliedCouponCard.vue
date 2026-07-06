<template>
	<div class="rounded-xl border border-secondary/30 bg-secondary-container/20 p-4 space-y-3">
		<div class="flex items-start justify-between gap-3">
			<div>
				<p class="text-label-sm uppercase tracking-wider text-on-surface-variant">
					Coupon Applied
				</p>
				<p class="text-body-md font-semibold text-on-surface">{{ couponCode }}</p>
			</div>
			<p class="text-body-md font-bold text-secondary">
				-{{ formatCurrency(discountAmount, currency) }}
			</p>
		</div>

		<div v-if="appointments?.length" class="space-y-1">
			<p class="text-label-sm text-on-surface-variant">Applied to:</p>
			<p class="text-body-sm text-on-surface">
				{{ appointments.map((row) => row.serviceType).join(", ") }}
			</p>
		</div>

		<slot />
	</div>
</template>

<script setup lang="ts">
import { formatCurrency } from "@/utils";
import type { CouponAppointmentBreakdown } from "@/services/checkout.service";

defineProps<{
	couponCode: string;
	discountAmount: number;
	currency: string;
	appointments?: CouponAppointmentBreakdown[];
}>();
</script>
