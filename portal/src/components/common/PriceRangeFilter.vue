<template>
	<div class="bg-white border-2 border-gray-200 rounded-lg px-6 py-6">
		<!-- Header -->
		<div class="flex items-center gap-2 mb-6">
			<!-- <FeatherIcon class="h-5 text-primary" name="dollar-sign" /> -->
			<span class="text-sm font-semibold text-gray-700">Price Range</span>
		</div>

		<!-- Slider Container -->
		<div class="relative pt-2 pb-8">
			<!-- Track Background -->
			<div class="absolute top-2 w-full h-1 bg-gray-200 rounded-full"></div>

			<!-- Active Track -->
			<div
				class="absolute top-2 h-1 bg-primary rounded-full"
				:style="{
					left: minPercent + '%',
					width: maxPercent - minPercent + '%',
				}"
			></div>

			<!-- Min Range Input -->
			<input
				type="range"
				:min="min"
				:max="max"
				:step="step"
				v-model.number="minValue"
				@input="updateMinValue"
				class="range-slider absolute w-full h-1 top-2 pointer-events-none appearance-none bg-transparent"
			/>

			<!-- Max Range Input -->
			<input
				type="range"
				:min="min"
				:max="max"
				:step="step"
				v-model.number="maxValue"
				@input="updateMaxValue"
				class="range-slider absolute w-full h-1 top-2 pointer-events-none appearance-none bg-transparent"
			/>

			<!-- Price Labels -->
			<div class="flex justify-between text-sm text-gray-600 mt-6">
				<span>${{ formatPrice(min) }}</span>
				<span>${{ formatPrice(max) }}</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({ min: 0, max: 1000 }),
	},
	min: {
		type: Number,
		default: 0,
	},
	max: {
		type: Number,
		default: 1000,
	},
	step: {
		type: Number,
		default: 10,
	},
});

const emit = defineEmits(["update:modelValue"]);

const minValue = ref(props.modelValue?.min ?? props.min);
const maxValue = ref(props.modelValue?.max ?? props.max);

// Watch for external changes to modelValue
watch(
	() => props.modelValue,
	(newValue) => {
		if (newValue) {
			minValue.value = newValue.min ?? props.min;
			maxValue.value = newValue.max ?? props.max;
		}
	},
	{ deep: true }
);

// Compute percentages for styling
const minPercent = computed(() => {
	return ((minValue.value - props.min) / (props.max - props.min)) * 100;
});

const maxPercent = computed(() => {
	return ((maxValue.value - props.min) / (props.max - props.min)) * 100;
});

function updateMinValue() {
	if (minValue.value > maxValue.value - props.step) {
		minValue.value = maxValue.value - props.step;
	}
	emitValue();
}

function updateMaxValue() {
	if (maxValue.value < minValue.value + props.step) {
		maxValue.value = minValue.value + props.step;
	}
	emitValue();
}

function emitValue() {
	emit("update:modelValue", {
		min: minValue.value,
		max: maxValue.value,
	});
}

function formatPrice(value) {
	return new Intl.NumberFormat("en-US", {
		minimumFractionDigits: 0,
		maximumFractionDigits: 0,
	}).format(value);
}
</script>

<style scoped>
/* Style for the range slider thumb */
.range-slider::-webkit-slider-thumb {
	pointer-events: all;
	width: 20px;
	height: 20px;
	border-radius: 50%;
	border: 3px solid white;
	background: #6366f1; /* primary color */
	cursor: pointer;
	appearance: none;
	box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
	position: relative;
	z-index: 10;
}

.range-slider::-moz-range-thumb {
	pointer-events: all;
	width: 20px;
	height: 20px;
	border-radius: 50%;
	border: 3px solid white;
	background: #6366f1;
	cursor: pointer;
	box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
	position: relative;
	z-index: 10;
}

.range-slider::-webkit-slider-thumb:hover {
	background: #4f46e5;
	transform: scale(1.1);
}

.range-slider::-moz-range-thumb:hover {
	background: #4f46e5;
	transform: scale(1.1);
}
</style>
