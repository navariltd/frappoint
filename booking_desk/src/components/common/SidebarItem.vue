<template>
	<RouterLink
		:to="to"
		class="group flex items-center justify-between px-3 py-2.5 rounded-sm transition-all duration-200"
		:class="[
			isActive
				? 'bg-white text-primary border-l-4 border-secondary shadow-sm'
				: 'text-white/80 border-l-4 border-transparent hover:bg-white/10 hover:text-white',
		]"
	>
		<div class="flex items-center gap-3">
			<span
				class="material-symbols-outlined text-[24px]"
				:class="isActive ? 'text-primary' : 'text-white/70 group-hover:text-white'"
			>
				{{ icon }}
			</span>
			<span
				class="text-md font-medium"
				:class="isActive ? 'text-primary' : 'text-white/80'"
				>{{ label }}</span
			>
		</div>

		<span
			v-if="count !== undefined"
			class="text-[10px] font-bold px-2 py-0.5 rounded-full border"
			:class="
				isActive
					? 'bg-secondary-container border-secondary/20 text-on-secondary-container'
					: 'bg-white/10 border-white/20 text-white'
			"
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
	activeWhen: { type: Array, default: () => [] },
});

const route = useRoute();
const isActive = computed(() => {
	const currentName = String(route.name || "");
	const explicitActiveNames = props.activeWhen.map((name) => String(name));

	if (explicitActiveNames.length) {
		return explicitActiveNames.includes(currentName);
	}

	return currentName === String(props.to.name || "");
});
</script>
