<template>
	<div
		class="rounded-xl border border-outline-variant bg-surface-container-lowest p-8 text-center"
	>
		<p class="text-[14px] font-semibold text-on-surface">Booking not found</p>
		<p class="text-[12px] text-on-surface-variant mt-1">
			The booking could not be loaded or has no linked data.
		</p>
		<button
			type="button"
			class="mt-4 rounded-lg bg-primary text-on-primary px-4 py-2 text-[12px] font-semibold"
			@click="$emit('retry')"
		>
			Retry
		</button>
	</div>
</template>

<script setup>
defineEmits(["retry"]);
</script>
