<template>
	<span
		class="px-3 py-1 bg-white/20 backdrop-blur-md border border-white/30 text-white text-xs font-semibold rounded-full"
		>{{ tag }}
	</span>
</template>

<script setup>
defineProps({
	tag: String,
});
</script>
