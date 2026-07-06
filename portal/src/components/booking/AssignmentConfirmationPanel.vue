<template>
	<div class="mt-auto pt-6 space-y-3">
		<button
			v-if="canConfirm"
			class="w-full px-6 py-3 rounded-full bg-primary text-on-primary font-semibold hover:opacity-90 disabled:opacity-50"
			:disabled="saving"
			@click="$emit('confirm')"
		>
			<span v-if="!saving">Confirm Assignment</span>
			<span v-else class="flex items-center justify-center gap-2">
				<span
					class="inline-block w-4 h-4 border-2 border-on-primary border-t-transparent rounded-full animate-spin"
				></span>
				Saving...
			</span>
		</button>

		<button
			v-else
			class="w-full px-6 py-3 rounded-full border border-outline-variant text-on-surface font-semibold opacity-50 cursor-not-allowed"
		>
			Select slot to continue
		</button>

		<button
			v-if="!workflowComplete"
			class="w-full px-6 py-3 rounded-full border border-primary text-primary font-semibold hover:bg-primary/5 disabled:opacity-50"
			:disabled="disablePrevious"
			@click="$emit('previous')"
		>
			← Previous
		</button>

		<button
			v-if="workflowComplete"
			class="w-full px-6 py-3 rounded-full bg-secondary text-on-secondary font-semibold hover:opacity-90"
			@click="$emit('proceed')"
		>
			Proceed to Payment →
		</button>
	</div>
</template>

<script setup lang="ts">
defineProps<{
	canConfirm: boolean;
	saving: boolean;
	workflowComplete: boolean;
	disablePrevious: boolean;
}>();

defineEmits<{
	confirm: [];
	previous: [];
	proceed: [];
}>();
</script>
