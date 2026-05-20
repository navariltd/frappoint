<template>
	<div
		:class="[
			'h-full min-h-[96px] bg-surface-container-lowest p-4 rounded-lg shadow-sm border border-outline-variant/40',
			borderLeftColor && `border-l-4 ${borderLeftColor}`,
		]"
	>
		<p class="text-[12px] text-on-surface-variant font-medium">{{ props.label }}</p>
		<div class="flex items-end justify-between mt-1">
			<span :class="['text-headline-sm font-headline-sm', numberColor, numberOpacity]">
				{{ props.number }}
			</span>
			<span v-if="props.percentage" class="text-[12px] text-secondary font-bold">{{
				props.percentage
			}}</span>
			<span
				:class="['material-symbols-outlined', iconColor, iconOpacity]"
				:style="iconStyle"
			>
				{{ props.icon }}
			</span>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	label: String,
	number: Number,
	percentage: String,
	icon: String,
	numberColor: {
		type: String,
		default: "text-primary",
	},
	iconColor: {
		type: String,
		default: "text-secondary",
	},
	borderLeftColor: {
		type: String,
		default: null,
	},
	iconFilled: {
		type: Boolean,
		default: false,
	},
	numberOpacity: {
		type: String,
		default: "",
	},
	iconOpacity: {
		type: String,
		default: "",
	},
});

const iconStyle = computed(() => {
	if (props.iconFilled) {
		return { fontVariationSettings: "'FILL' 1" };
	}
	return {};
});
</script>
