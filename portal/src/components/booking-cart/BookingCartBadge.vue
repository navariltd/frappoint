<template>
	<div v-if="totalQuantity > 0" class="relative">
		<button
			class="relative inline-flex items-center justify-center w-10 h-10 rounded-full bg-primary text-on-primary hover:bg-primary/90 transition-colors"
			@click="$emit('click')"
			:aria-label="`Shopping cart with ${totalQuantity} items`"
		>
			<span class="material-symbols-outlined text-[20px]">shopping_cart</span>
			<span
				v-if="totalQuantity > 0"
				class="absolute -top-1 -right-1 inline-flex items-center justify-center px-2 py-0.5 text-xs font-semibold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-error rounded-full min-w-[20px]"
			>
				{{ totalQuantity }}
			</span>
		</button>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useBookingCart } from "@/composables/useBookingCart";

defineEmits<{
	click: [];
}>();

const { totalQuantity } = useBookingCart();
</script>
