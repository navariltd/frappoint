<template>
	<div class="flex gap-3 flex-wrap">
		<div class="bg-surface-container-high px-4 py-2 rounded-xl min-w-[92px]">
			<p class="text-label-sm text-outline">Total</p>
			<p class="text-headline-sm font-bold text-on-surface">{{ metrics.total }}</p>
		</div>
		<div class="bg-secondary-container px-4 py-2 rounded-xl min-w-[92px]">
			<p class="text-label-sm text-on-secondary-container">Running</p>
			<p class="text-headline-sm font-bold text-on-secondary-container">
				{{ metrics.inProgress }}
			</p>
		</div>
		<div class="bg-error-container px-4 py-2 rounded-xl min-w-[92px]">
			<p class="text-label-sm text-on-error-container">Delayed</p>
			<p class="text-headline-sm font-bold text-on-error-container">{{ metrics.delayed }}</p>
		</div>
	</div>
</template>

<script setup>
defineProps({
	metrics: {
		type: Object,
		required: true,
	},
});
</script>
