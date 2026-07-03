<template>
	<div class="space-y-2">
		<div class="flex justify-between text-label-sm">
			<span class="text-on-surface-variant">Progress</span>
			<span class="font-semibold text-on-surface">{{ completed }}/{{ total }}</span>
		</div>
		<div class="h-2 bg-outline-variant/20 rounded-full overflow-hidden">
			<div
				class="h-full bg-primary transition-all duration-300"
				:style="{ width: `${percent}%` }"
			></div>
		</div>
	</div>
</template>

<script setup lang="ts">
defineProps<{
	total: number;
	completed: number;
	percent: number;
}>();
</script>
