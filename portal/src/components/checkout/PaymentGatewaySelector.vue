<template>
	<div class="space-y-3">
		<GatewayCard
			v-for="gateway in gateways"
			:key="gateway.id"
			:gateway="gateway"
			:selected="selectedId === gateway.id"
			@select="$emit('select', gateway.id)"
		/>

		<div
			v-if="!gateways.length"
			class="p-6 text-center rounded-lg border border-outline-variant/20"
		>
			<span class="material-symbols-outlined text-on-surface-variant text-[32px] mb-2 block">
				payments
			</span>
			<p class="text-body-sm text-on-surface-variant">
				No online payment methods are currently available.
			</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import GatewayCard from "./GatewayCard.vue";
import type { OnlineGateway } from "@/services/checkout.service";

defineProps<{
	gateways: OnlineGateway[];
	selectedId: string;
}>();

defineEmits<{
	select: [gatewayId: string];
}>();
</script>
