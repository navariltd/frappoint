<template>
	<div class="inline-flex rounded-xl bg-surface-container p-1">
		<button
			v-for="view in views"
			:key="view.value"
			type="button"
			class="px-3 py-2 rounded-lg text-[12px] font-semibold transition-colors"
			:class="
				modelValue === view.value
					? 'bg-primary-container text-on-primary-container shadow-sm'
					: 'text-on-surface-variant hover:text-on-surface'
			"
			@click="$emit('update:modelValue', view.value)"
		>
			{{ view.label }}
		</button>
	</div>
</template>

<script setup>
defineProps({
	modelValue: { type: String, required: true },
	views: { type: Array, default: () => [] },
});

defineEmits(["update:modelValue"]);
</script>
