<template>
	<div class="mt-auto pt-3 flex gap-2 justify-between">
		<button
			class="flex-1 py-1.5 bg-surface-container text-on-surface-variant hover:bg-secondary-container hover:text-on-secondary-container transition-colors rounded-lg text-label-sm font-semibold"
			@click="$emit('action', 'open')"
		>
			Open
		</button>
		<!-- <button
			class="px-2 py-1.5 bg-primary text-on-primary hover:opacity-90 transition-opacity rounded-lg text-label-sm font-semibold"
			@click="$emit('action', 'checkin')"
		>
			Check In
		</button> -->
	</div>
</template>

<script setup>
defineEmits(["action"]);
</script>
