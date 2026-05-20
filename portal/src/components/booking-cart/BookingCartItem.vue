<template>
	<div class="flex items-start gap-4 py-4 border-b border-outline-variant/20">
		<!-- Service Image -->
		<div class="flex-shrink-0 w-20 h-20 rounded-lg bg-outline-variant/10 overflow-hidden">
			<img
				v-if="item.image"
				:src="item.image"
				:alt="item.service_name"
				class="w-full h-full object-cover"
			/>
			<div v-else class="w-full h-full flex items-center justify-center">
				<span class="material-symbols-outlined text-outline-variant">spa</span>
			</div>
		</div>

		<!-- Item Details -->
		<div class="flex-1 min-w-0">
			<h4 class="font-semibold text-body-lg text-on-surface truncate">
				{{ item.service_name }}
			</h4>
			<p class="text-body-sm text-on-surface-variant">{{ item.package_name }}</p>
			<p class="text-body-sm text-on-surface-variant">{{ item.duration_minutes }} min</p>
		</div>

		<!-- Price -->
		<div class="flex-shrink-0 text-right">
			<p class="font-semibold text-body-lg text-on-surface">
				{{ currency }}{{ (item.price * item.quantity).toFixed(2) }}
			</p>
			<p class="text-body-sm text-on-surface-variant">
				{{ currency }}{{ item.price.toFixed(2) }} each
			</p>
		</div>

		<!-- Quantity Controls -->
		<div class="flex-shrink-0 flex items-center gap-2 bg-outline-variant/10 rounded-lg p-1">
			<button
				class="p-1.5 rounded hover:bg-outline-variant/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				@click="$emit('decrement')"
				:aria-label="`Decrease quantity of ${item.service_name}`"
			>
				<span class="material-symbols-outlined text-[18px]">remove</span>
			</button>
			<span class="w-6 text-center text-body-sm font-semibold">
				{{ item.quantity }}
			</span>
			<button
				class="p-1.5 rounded hover:bg-outline-variant/20 transition-colors"
				@click="$emit('increment')"
				:aria-label="`Increase quantity of ${item.service_name}`"
			>
				<span class="material-symbols-outlined text-[18px]">add</span>
			</button>
		</div>

		<!-- Remove Button -->
		<button
			class="flex-shrink-0 p-2 rounded-full hover:bg-error/10 transition-colors"
			@click="$emit('remove')"
			:aria-label="`Remove ${item.service_name} from cart`"
		>
			<span class="material-symbols-outlined text-error">close</span>
		</button>
	</div>
</template>

<script setup lang="ts">
import type { CartItem } from "@/stores/bookingCart.store";

defineProps<{
	item: CartItem;
	currency: string;
}>();

defineEmits<{
	increment: [];
	decrement: [];
	remove: [];
}>();
</script>
