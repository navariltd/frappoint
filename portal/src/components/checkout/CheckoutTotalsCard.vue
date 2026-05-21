<template>
	<div class="space-y-3">
		<div class="flex justify-between items-center text-body-sm">
			<span class="text-on-surface-variant">Subtotal</span>
			<span class="font-semibold text-on-surface">{{
				formatCurrency(booking.subtotal, currency)
			}}</span>
		</div>

		<div v-if="depositSelected" class="flex justify-between items-center text-body-sm">
			<span class="text-on-surface-variant">Deposit ({{ depositPercent }}%)</span>
			<span class="font-semibold text-on-surface">{{
				formatCurrency(depositAmount, currency)
			}}</span>
		</div>

		<div class="border-t border-outline-variant/20 pt-3 flex justify-between items-baseline">
			<span class="text-headline-sm font-semibold text-on-surface">
				{{ depositSelected ? "Amount Due Now" : "Total Due" }}
			</span>
			<span class="text-headline-sm font-bold text-primary">
				{{ formatCurrency(payableAmount, currency) }}
			</span>
		</div>

		<div
			v-if="depositSelected && remainingAfterPayment > 0"
			class="flex justify-between items-center text-label-sm text-on-surface-variant"
		>
			<span>Remaining after payment</span>
			<span>{{ formatCurrency(remainingAfterPayment, currency) }}</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { formatCurrency } from "@/utils";
import type { CheckoutBookingSummary } from "@/services/checkout.service";

const props = defineProps<{
	booking: CheckoutBookingSummary;
	payableAmount: number;
	depositAmount: number;
	depositPercent: number;
	remainingAfterPayment: number;
	currency: string;
	paymentType: "full" | "deposit";
}>();

const depositSelected = computed(() => props.paymentType === "deposit");
</script>
