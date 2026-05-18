<template>
	<RouterLink
		:to="to"
		class="group flex items-center justify-between px-3 py-2.5 rounded-sm transition-all duration-200"
		:class="[
			isActive
				? 'bg-primary/10 text-primary border-l-4 border-primary'
				: 'text-text-sub-light dark:text-text-sub-dark hover:bg-gray-100 dark:hover:bg-gray-800',
		]"
	>
		<div class="flex items-center gap-3">
			<span
				class="material-symbols-outlined text-[24px]"
				:class="isActive ? 'text-primary' : 'text-gray-400 group-hover:text-gray-600'"
			>
				{{ icon }}
			</span>
			<span
				class="text-md font-medium"
				:class="isActive ? 'text-primary' : 'text-gray-400'"
				>{{ label }}</span
			>
		</div>

		<span
			v-if="count !== undefined"
			class="text-[10px] font-bold px-2 py-0.5 rounded-full border"
			:class="isActive ? 'bg-white border-blue-100' : 'bg-gray-100 border-transparent'"
		>
			{{ count }}
		</span>
	</RouterLink>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";

const props = defineProps({
	to: { type: Object, required: true },
	icon: { type: String, required: true },
	label: { type: String, required: true },
	count: { type: [Number, String], default: undefined },
});

const route = useRoute();
// Checks if the current route name matches the link destination
const isActive = computed(() => route.name === props.to.name);
</script>
