<template>
	<div v-if="issues.length" class="rounded-xl border border-error/30 bg-error-container/30 p-3">
		<p class="text-[12px] font-semibold text-error mb-1">Checkout validation</p>
		<ul class="text-[12px] text-on-surface space-y-1">
			<li v-for="issue in issues" :key="issue">{{ issue }}</li>
		</ul>
	</div>
</template>

<script setup>
defineProps({
	issues: {
		type: Array,
		default: () => [],
	},
});
</script>
