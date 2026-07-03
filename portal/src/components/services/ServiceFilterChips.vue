<template>
	<div v-if="chips.length" class="flex flex-wrap gap-2 mb-6">
		<button
			v-for="chip in chips"
			:key="chip.key"
			type="button"
			class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary-container text-on-secondary-container text-[12px]"
			@click="$emit('remove', chip)"
		>
			<span>{{ chip.label }}</span>
			<span aria-hidden="true">×</span>
		</button>
		<button
			type="button"
			class="px-3 py-1.5 rounded-full bg-surface-container-low border border-outline-variant text-[12px] text-on-surface"
			@click="$emit('clear')"
		>
			Clear All
		</button>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	filters: { type: Object, required: true },
});

defineEmits(["remove", "clear"]);

const chips = computed(() => {
	const list = [];
	if (props.filters.search) {
		list.push({ key: "search", type: "search", label: `Search: ${props.filters.search}` });
	}
	if (props.filters.date) {
		list.push({ key: "date", type: "date", label: `Date: ${props.filters.date}` });
	}
	if (Number(props.filters.guests || 1) > 1) {
		list.push({ key: "guests", type: "guests", label: `Guests: ${props.filters.guests}` });
	}
	if (props.filters.duration) {
		list.push({
			key: "duration",
			type: "duration",
			value: props.filters.duration,
			label: `${props.filters.duration} min`,
		});
	}
	for (const category of props.filters.categories || []) {
		list.push({
			key: `category-${category}`,
			type: "category",
			value: category,
			label: category,
		});
	}
	return list;
});
</script>
