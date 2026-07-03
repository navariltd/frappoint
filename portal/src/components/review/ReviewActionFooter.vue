<template>
	<div class="border-t border-outline-variant/20 bg-surface px-6 py-5">
		<div class="max-w-7xl mx-auto flex items-center justify-between gap-4">
			<div>
				<p class="text-label-sm text-on-surface-variant">Total payable</p>
				<p class="text-headline-md font-headline-md text-primary">
					{{ fmt(finalAmount) }}
				</p>
			</div>
			<button
				:disabled="!canProceed || isLoading"
				class="inline-flex items-center gap-2 px-8 py-3 rounded-full bg-primary text-on-primary font-semibold text-body-md hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
				@click="$emit('proceed')"
			>
				<span
					v-if="isLoading"
					class="w-5 h-5 border-2 border-on-primary/30 border-t-on-primary rounded-full animate-spin"
				></span>
				<span v-else class="material-symbols-outlined text-[20px]">arrow_forward</span>
				Proceed to Checkout
			</button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { formatCurrency } from "@/utils";

const props = defineProps<{
	finalAmount: number;
	currency: string;
	canProceed: boolean;
	isLoading: boolean;
}>();

defineEmits<{ proceed: [] }>();

function fmt(amount: number) {
	return formatCurrency(Number(amount || 0), props.currency);
}
</script>
