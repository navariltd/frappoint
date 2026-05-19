<template>
	<div class="flex flex-wrap gap-2">
		<button
			type="button"
			class="rounded-lg border border-outline px-4 py-2 text-[12px] font-semibold"
			@click="$emit('refresh')"
		>
			Refresh
		</button>
		<button
			type="button"
			class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[12px] font-semibold disabled:opacity-60"
			:disabled="!canSubmit || isSubmitting"
			@click="$emit('submit')"
		>
			{{ isSubmitting ? "Processing..." : submitLabel }}
		</button>
	</div>
</template>

<script setup>
defineProps({
	submitLabel: {
		type: String,
		default: "Process Payment",
	},
	canSubmit: {
		type: Boolean,
		default: false,
	},
	isSubmitting: {
		type: Boolean,
		default: false,
	},
});

defineEmits(["submit", "refresh"]);
</script>
