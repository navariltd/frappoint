<template>
	<section class="rounded-xl border border-outline-variant/30 bg-surface-container-low p-6">
		<div class="mb-4 flex items-center gap-3">
			<span class="material-symbols-outlined text-primary">spa</span>
			<h3 class="font-headline-sm text-headline-sm text-on-surface">Techniques</h3>
		</div>

		<ul class="space-y-3 text-on-surface-variant font-body-md text-body-md">
			<li v-for="item in items" :key="item" class="flex items-start gap-3">
				<span class="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-secondary"></span>
				<span>{{ item }}</span>
			</li>
		</ul>
	</section>
</template>

<script setup>
const props = defineProps({
	items: {
		type: [Array, String],
		default: () => [],
	},
});
</script>
