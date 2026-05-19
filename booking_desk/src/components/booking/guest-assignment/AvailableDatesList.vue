<template>
	<div class="flex flex-wrap gap-2">
		<button
			v-for="dateRow in dates"
			:key="dateRow.date"
			type="button"
			class="rounded-full border px-3 py-1.5 text-[11px]"
			:class="
				selectedDate === dateRow.date
					? 'border-primary bg-primary text-on-primary'
					: 'border-outline-variant bg-surface text-on-surface hover:bg-surface-container'
			"
			@click="$emit('select', dateRow.date)"
		>
			{{ dateRow.label }}
		</button>
	</div>
</template>

<script setup>
defineProps({
	dates: {
		type: Array,
		default: () => [],
	},
	selectedDate: {
		type: String,
		default: "",
	},
});

defineEmits(["select"]);
</script>
