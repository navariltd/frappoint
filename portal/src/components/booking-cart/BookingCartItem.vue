<template>
	<div class="flex flex-wrap items-start gap-3 py-4 border-b border-outline-variant/20">
		<div class="flex min-w-0 flex-1 items-start gap-4">
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
		</div>

		<div class="flex w-full items-center justify-between gap-2">
			<!-- Price -->
			<div class="flex-shrink-0 text-left">
				<p class="font-semibold text-body-lg text-on-surface whitespace-nowrap">
					{{ currency }}{{ (item.price * item.quantity).toFixed(2) }}
				</p>
				<p class="text-body-sm text-on-surface-variant whitespace-nowrap">
					{{ currency }}{{ item.price.toFixed(2) }} each
				</p>
			</div>

			<!-- Quantity Controls + Remove -->
			<div class="flex flex-shrink-0 items-center gap-2">
				<div class="flex items-center gap-2 bg-outline-variant/10 rounded-lg p-1">
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
					class="p-2 rounded-full hover:bg-error/10 transition-colors"
					@click="$emit('remove')"
					:aria-label="`Remove ${item.service_name} from cart`"
				>
					<span class="material-symbols-outlined text-error">close</span>
				</button>
			</div>
		</div>
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
