<template>
	<section class="rounded-xl border border-outline-variant/30 bg-surface-container-low p-6">
		<div class="mb-4 flex items-center gap-3">
			<span class="material-symbols-outlined text-primary">clinical_notes</span>
			<h3 class="font-headline-sm text-headline-sm text-on-surface">Benefits</h3>
		</div>

		<!-- Render raw HTML if provided -->
		<div
			v-if="rawHtml"
			class="prose prose-sm max-w-none text-on-surface-variant font-body-md text-body-md"
			v-html="rawHtml"
		></div>

		<!-- Fallback to array rendering -->
		<ul
			v-else-if="items.length"
			class="space-y-3 text-on-surface-variant font-body-md text-body-md"
		>
			<li v-for="item in items" :key="item" class="flex items-start gap-3">
				<span class="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary"></span>
				<span>{{ item }}</span>
			</li>
		</ul>

		<p v-else class="text-body-md text-on-surface-variant/70">No benefits listed yet.</p>
	</section>
</template>

<script setup>
const props = defineProps({
	items: {
		type: [Array, String],
		default: () => [],
	},
	rawHtml: {
		type: String,
		default: "",
	},
});
</script>
