<template>
	<button
		type="button"
		class="rounded-lg border px-3 py-2 text-left"
		:class="[
			selected
				? 'border-primary bg-primary text-on-primary'
				: slot.availability === 'partial'
				? 'border-tertiary bg-tertiary-container/40 text-on-surface'
				: 'border-outline-variant bg-surface text-on-surface hover:bg-surface-container',
		]"
		:disabled="disabled"
		@click="!disabled && $emit('select', slot.id)"
	>
		<div class="flex items-start justify-between gap-2">
			<div class="min-w-0">
				<p class="text-[12px] font-semibold">{{ slot.startTime }} - {{ slot.endTime }}</p>
				<p class="text-[11px] opacity-80">{{ slot.providerSummary }}</p>
			</div>
			<span
				v-if="pending"
				class="material-symbols-outlined text-[16px] animate-spin shrink-0"
			>
				progress_activity
			</span>
		</div>
	</button>
</template>

<script setup>
defineProps({
	slot: {
		type: Object,
		required: true,
	},
	selected: {
		type: Boolean,
		default: false,
	},
	pending: {
		type: Boolean,
		default: false,
	},
	disabled: {
		type: Boolean,
		default: false,
	},
});

defineEmits(["select"]);
</script>
