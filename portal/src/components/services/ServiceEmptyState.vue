<template>
	<div
		class="rounded-xl border border-outline-variant/30 bg-surface-container-low p-10 text-center"
	>
		<h3 class="font-headline-sm text-headline-sm text-on-surface mb-2">No services found</h3>
		<p class="font-body-md text-body-md text-on-surface-variant mb-5">
			Try adjusting your filters to discover more services.
		</p>
		<button
			type="button"
			class="bg-primary text-on-primary px-5 py-2.5 rounded-full font-label-md text-label-md hover:opacity-90 transition-all"
			@click="$emit('clear')"
		>
			Reset Filters
		</button>
	</div>
</template>

<script setup>
defineEmits(["clear"]);
</script>
