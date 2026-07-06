<template>
	<div
		class="rounded-xl border border-outline-variant bg-surface-container-lowest p-8 text-center"
	>
		<p class="text-[14px] text-on-surface">No appointments found for the selected range.</p>
		<button class="mt-3 text-[12px] font-semibold text-primary" @click="$emit('refresh')">
			Refresh
		</button>
	</div>
</template>

<script setup>
defineEmits(["refresh"]);
</script>
