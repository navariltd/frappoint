<template>
	<div
		v-if="totalSavings > 0"
		class="rounded-xl border border-secondary/20 bg-secondary-container/10 p-4 space-y-2"
	>
		<div class="flex justify-between items-center text-body-sm">
			<span class="text-on-surface-variant">Total savings</span>
			<span class="font-semibold text-secondary"
				>-{{ formatCurrency(totalSavings, currency) }}</span
			>
		</div>
		<div class="flex justify-between items-center text-body-sm">
			<span class="text-on-surface-variant">Discounted subtotal</span>
			<span class="font-semibold text-on-surface">{{
				formatCurrency(discountedTotal, currency)
			}}</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import { formatCurrency } from "@/utils";

defineProps<{
	totalSavings: number;
	discountedTotal: number;
	currency: string;
}>();
</script>
