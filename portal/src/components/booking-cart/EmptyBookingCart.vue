<template>
	<div class="flex flex-col items-center justify-center py-12 px-6 text-center">
		<div
			class="w-16 h-16 rounded-full bg-outline-variant/10 flex items-center justify-center mb-4"
		>
			<span class="material-symbols-outlined text-4xl text-outline-variant"
				>shopping_cart</span
			>
		</div>
		<h3 class="text-headline-sm font-headline-sm text-on-surface mb-2">Your cart is empty</h3>
		<p class="text-body-md text-on-surface-variant mb-6">
			Add services from our catalog to get started with your booking.
		</p>
		<button
			class="px-6 py-2.5 rounded-full bg-primary text-on-primary font-semibold text-body-md hover:bg-primary/90 transition-colors"
			@click="$emit('browse')"
		>
			Browse Services
		</button>
	</div>
</template>

<script setup lang="ts">
defineEmits<{
	browse: [];
}>();
</script>
