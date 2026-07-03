<template>
	<div class="bg-surface-container-low rounded-lg p-6 space-y-4">
		<!-- Service Count -->
		<div class="flex justify-between items-center text-body-md">
			<span class="text-on-surface-variant">Services</span>
			<span class="font-semibold text-on-surface">{{ cartCount }}</span>
		</div>

		<!-- Divider -->
		<div class="border-t border-outline-variant/20"></div>

		<!-- Subtotal -->
		<div class="flex justify-between items-center text-headline-sm">
			<span class="text-on-surface">Subtotal</span>
			<span class="font-semibold text-primary">
				{{ currency }}{{ cartSubtotal.toFixed(2) }}
			</span>
		</div>

		<!-- Info Note -->
		<p class="text-body-sm text-on-surface-variant pt-2">
			✓ Prices are estimates. Final pricing will be confirmed during booking.
		</p>
	</div>
</template>

<script setup lang="ts">
import { useBookingCart } from "@/composables/useBookingCart";

const { cartCount, totalQuantity, cartSubtotal, currency } = useBookingCart();
</script>
