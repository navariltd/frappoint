<template>
	<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
		<div
			v-for="idx in count"
			:key="idx"
			class="bg-surface-container-lowest rounded-xl border border-outline-variant/20 overflow-hidden animate-pulse"
		>
			<div class="aspect-[16/9] bg-surface-container-low"></div>
			<div class="p-stack-md space-y-3">
				<div class="h-5 w-2/3 bg-surface-container-low rounded"></div>
				<div class="h-4 w-full bg-surface-container-low rounded"></div>
				<div class="h-4 w-4/5 bg-surface-container-low rounded"></div>
				<div class="h-10 w-full bg-surface-container-low rounded-full"></div>
			</div>
		</div>
	</div>
</template>

<script setup>
defineProps({
	count: { type: Number, default: 6 },
});
</script>
