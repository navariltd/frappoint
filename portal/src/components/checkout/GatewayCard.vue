<template>
	<button
		class="w-full p-4 rounded-xl border-2 flex items-center gap-4 cursor-pointer transition-all text-left"
		:class="
			selected
				? 'border-primary bg-primary-container/10'
				: 'border-outline-variant/30 bg-surface hover:border-primary/40 hover:bg-surface-container'
		"
		type="button"
		@click="$emit('select', gateway.id)"
	>
		<!-- Icon / Logo -->
		<div
			class="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 font-bold text-body-lg"
			:class="
				selected
					? 'bg-primary text-on-primary'
					: 'bg-surface-container-high text-on-surface-variant'
			"
		>
			<span v-if="isMpesa" class="text-body-md font-extrabold">M</span>
			<span v-else class="material-symbols-outlined text-[22px]">credit_card</span>
		</div>

		<!-- Details -->
		<div class="flex-1 min-w-0">
			<p class="text-body-md font-semibold text-on-surface">{{ gateway.name }}</p>
			<p class="text-label-sm text-on-surface-variant mt-0.5">{{ gatewayDescription }}</p>
		</div>

		<!-- Radio indicator -->
		<div
			class="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all"
			:class="selected ? 'border-primary bg-primary' : 'border-outline-variant'"
		>
			<div v-if="selected" class="w-2 h-2 rounded-full bg-on-primary"></div>
		</div>
	</button>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { OnlineGateway } from "@/services/checkout.service";

const props = defineProps<{
	gateway: OnlineGateway;
	selected: boolean;
}>();

defineEmits<{
	select: [id: string];
}>();

const isMpesa = computed(() => props.gateway.providerType === "mpesa");

const gatewayDescription = computed(() => {
	if (props.gateway.details) return props.gateway.details;
	if (props.gateway.providerType === "mpesa") return "Direct M-Pesa push to your phone";
	return "Secure hosted payment page";
});
</script>
