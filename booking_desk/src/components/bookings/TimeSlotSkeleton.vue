<template>
	<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 sm:gap-3 animate-pulse">
		<div v-for="i in count" :key="i" class="h-12 bg-gray-200 rounded-lg"></div>
	</div>
</template>

<script setup>
defineProps({
	count: {
		type: Number,
		default: 8,
	},
});
</script>
