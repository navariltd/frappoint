<template>
	<div class="flex flex-wrap gap-2">
		<button
			type="button"
			class="rounded-md bg-primary text-on-primary px-3.5 py-2 text-[12px] font-semibold transition-colors hover:bg-primary-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40"
			@click="$emit('open')"
		>
			Open
		</button>
		<button
			type="button"
			class="rounded-md border border-outline-variant/70 text-on-surface-variant px-3.5 py-2 text-[12px] font-semibold transition-colors hover:bg-surface-container-high focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/30"
			@click="$emit('reschedule')"
		>
			Reschedule
		</button>
		<button
			type="button"
			class="rounded-md border border-error/70 text-error px-3.5 py-2 text-[12px] font-semibold transition-colors hover:bg-error/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-error/30"
			@click="$emit('cancel')"
		>
			Cancel
		</button>
	</div>
</template>

<script setup>
defineEmits(["open", "reschedule", "cancel"]);
</script>
