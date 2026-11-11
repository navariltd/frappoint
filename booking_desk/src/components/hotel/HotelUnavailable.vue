<template>
	<div
		class="rounded-xl border border-outline-variant bg-surface-container-lowest p-8 text-center"
	>
		<span class="material-symbols-outlined text-[32px] text-on-surface-variant">hotel</span>
		<p class="mt-2 text-[14px] font-semibold text-on-surface">{{ message }}</p>
	</div>
</template>

<script setup>
defineProps({ message: { type: String, required: true } });
</script>
