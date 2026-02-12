<template>
	<div class="relative">
		<div
			class="flex items-center gap-2 px-4 py-2.5 bg-white border-2 border-gray-200 rounded-lg hover:border-primary/50 transition-all cursor-pointer group"
			:class="{ 'border-primary': isOpen }"
			@click="toggleDropdown"
		>
			<FeatherIcon
				class="h-4 flex-shrink-0 transition-colors"
				:class="selectedRange ? 'text-primary' : 'text-gray-400 group-hover:text-primary'"
				name="dollar-sign"
			/>
			<span
				class="flex-1 text-sm md:text-base truncate transition-colors"
				:class="
					selectedRange
						? 'text-gray-900 font-medium'
						: 'text-gray-500 group-hover:text-gray-700'
				"
			>
				{{ displayText }}
			</span>
			<FeatherIcon
				class="h-4 flex-shrink-0 text-gray-400 transition-transform"
				:class="{ 'rotate-180': isOpen }"
				name="chevron-down"
			/>
		</div>

		<!-- Dropdown Menu -->
		<Transition
			enter-active-class="transition ease-out duration-100"
			enter-from-class="transform opacity-0 scale-95"
			enter-to-class="transform opacity-100 scale-100"
			leave-active-class="transition ease-in duration-75"
			leave-from-class="transform opacity-100 scale-100"
			leave-to-class="transform opacity-0 scale-95"
		>
			<div
				v-if="isOpen"
				class="absolute z-50 mt-2 w-full bg-white rounded-lg shadow-lg border border-gray-200 py-1 max-h-60 overflow-y-auto"
			>
				<div
					@click="selectOption(null)"
					class="px-4 py-2.5 text-sm md:text-base cursor-pointer transition-colors flex items-center gap-2"
					:class="
						!selectedRange
							? 'bg-primary/10 text-primary font-medium'
							: 'text-gray-700 hover:bg-gray-50'
					"
				>
					<FeatherIcon
						v-if="!selectedRange"
						class="h-4 text-primary flex-shrink-0"
						name="check"
					/>
					<span :class="{ 'ml-6': selectedRange }">All Prices</span>
				</div>
				<div
					v-for="range in priceRanges"
					:key="range.value"
					@click="selectOption(range)"
					class="px-4 py-2.5 text-sm md:text-base cursor-pointer transition-colors flex items-center gap-2 whitespace-nowrap"
					:class="
						selectedRange === range.value
							? 'bg-primary/10 text-primary font-medium'
							: 'text-gray-700 hover:bg-gray-50'
					"
				>
					<FeatherIcon
						v-if="selectedRange === range.value"
						class="h-4 text-primary flex-shrink-0"
						name="check"
					/>
					<span :class="{ 'ml-6': selectedRange !== range.value }">
						{{ range.label }}
					</span>
				</div>
			</div>
		</Transition>
	</div>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui";
import { computed, ref, watch, onMounted, onUnmounted } from "vue";
import { formatCurrency } from "@/utils";

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
	currency: {
		type: String,
		default: "USD",
	},
});

const emit = defineEmits(["update:modelValue"]);

const isOpen = ref(false);

// Dynamically generate price ranges based on min and max props
const priceRanges = computed(() => {
	const range = props.max - props.min;
	const step = Math.ceil(range / 5); // Divide into 5 ranges
	const ranges = [];

	for (let i = 0; i < 4; i++) {
		const rangeMin = props.min + step * i;
		const rangeMax = props.min + step * (i + 1);
		ranges.push({
			label: `${formatCurrency(rangeMin, props.currency)} - ${formatCurrency(
				rangeMax,
				props.currency
			)}`,
			value: `${rangeMin}-${rangeMax}`,
			min: rangeMin,
			max: rangeMax,
		});
	}

	// Last range is "X+"
	const lastMin = props.min + step * 4;
	ranges.push({
		label: `${formatCurrency(lastMin, props.currency)}+`,
		value: `${lastMin}+`,
		min: lastMin,
		max: props.max,
	});

	return ranges;
});

const selectedRange = ref("");

const displayText = computed(() => {
	if (!selectedRange.value) {
		return "All Prices";
	}
	const range = priceRanges.value.find((r) => r.value === selectedRange.value);
	return range ? range.label : "All Prices";
});

// Initialize selected range based on modelValue
watch(
	() => props.modelValue,
	(newValue) => {
		if (newValue && (newValue.min !== props.min || newValue.max !== props.max)) {
			const matchingRange = priceRanges.value.find(
				(r) => r.min === newValue.min && r.max === newValue.max
			);
			selectedRange.value = matchingRange ? matchingRange.value : "";
		} else {
			selectedRange.value = "";
		}
	},
	{ immediate: true }
);

function toggleDropdown() {
	isOpen.value = !isOpen.value;
}

function selectOption(range) {
	if (!range) {
		selectedRange.value = "";
		emit("update:modelValue", { min: props.min, max: props.max });
	} else {
		selectedRange.value = range.value;
		emit("update:modelValue", { min: range.min, max: range.max });
	}
	isOpen.value = false;
}

function closeDropdown(event) {
	if (!event.target.closest(".relative")) {
		isOpen.value = false;
	}
}

onMounted(() => {
	document.addEventListener("click", closeDropdown);
});

onUnmounted(() => {
	document.removeEventListener("click", closeDropdown);
});
</script>
