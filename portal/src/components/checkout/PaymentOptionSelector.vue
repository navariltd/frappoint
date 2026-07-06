<template>
	<div class="bg-surface-container-low rounded-full p-1.5 flex items-center">
		<button
			class="flex-1 py-3 px-5 rounded-full font-label-md font-semibold transition-all"
			:class="
				selected === 'full'
					? 'bg-primary text-on-primary shadow-md'
					: 'text-on-surface-variant hover:bg-surface-container'
			"
			@click="$emit('select', 'full')"
			type="button"
		>
			Pay Full Amount
		</button>
		<button
			v-if="depositEnabled"
			class="flex-1 py-3 px-5 rounded-full font-label-md font-semibold transition-all"
			:class="
				selected === 'deposit'
					? 'bg-primary text-on-primary shadow-md'
					: 'text-on-surface-variant hover:bg-surface-container'
			"
			@click="$emit('select', 'deposit')"
			type="button"
		>
			Pay Deposit
		</button>
	</div>
</template>

<script setup lang="ts">
import type { PaymentType } from "@/stores/checkout.store";

defineProps<{
	selected: PaymentType;
	depositEnabled: boolean;
}>();

defineEmits<{
	select: [type: PaymentType];
}>();
</script>
