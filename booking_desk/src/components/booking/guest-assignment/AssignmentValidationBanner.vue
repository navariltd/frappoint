<template>
	<div
		v-if="issues.length"
		class="rounded-xl border border-error-container bg-error-container/30 px-4 py-3"
	>
		<p class="text-[12px] font-semibold text-error">Fix these assignment issues</p>
		<ul class="mt-2 space-y-1 text-[12px] text-on-surface">
			<li v-for="issue in issues" :key="issue">• {{ issue }}</li>
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
