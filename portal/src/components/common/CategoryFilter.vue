<template>
	<div class="relative">
		<div
			class="flex items-center gap-2 px-4 py-2.5 bg-white border-2 border-gray-200 rounded-lg hover:border-primary/50 transition-all cursor-pointer group"
			:class="{ 'border-primary': isOpen }"
			@click="toggleDropdown"
		>
			<FeatherIcon
				class="h-4 flex-shrink-0 transition-colors"
				:class="
					selectedCategory ? 'text-primary' : 'text-gray-400 group-hover:text-primary'
				"
				name="filter"
			/>
			<span
				class="flex-1 text-sm md:text-base truncate transition-colors"
				:class="
					selectedCategory
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
					v-for="option in options"
					:key="option.value"
					@click="selectOption(option)"
					class="px-4 py-2.5 text-sm md:text-base cursor-pointer transition-colors flex items-center gap-2"
					:class="
						selectedCategory === option.value
							? 'bg-primary/10 text-primary font-medium'
							: 'text-gray-700 hover:bg-gray-50'
					"
				>
					<FeatherIcon
						v-if="selectedCategory === option.value"
						class="h-4 text-primary flex-shrink-0"
						name="check"
					/>
					<span :class="{ 'ml-6': selectedCategory !== option.value }">
						{{ option.label }}
					</span>
				</div>
			</div>
		</Transition>
	</div>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui";
import { computed, ref, onMounted, onUnmounted } from "vue";

const props = defineProps({
	modelValue: {
		type: [String, Number, null],
		default: null,
	},
	options: {
		type: Array,
		required: true,
		default: () => [],
	},
	placeholder: {
		type: String,
		default: "Select an option",
	},
});

const emit = defineEmits(["update:modelValue"]);

const isOpen = ref(false);

const selectedCategory = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

const displayText = computed(() => {
	if (selectedCategory.value === null) {
		return props.placeholder;
	}
	const selected = props.options.find((opt) => opt.value === selectedCategory.value);
	return selected ? selected.label : props.placeholder;
});

function toggleDropdown() {
	isOpen.value = !isOpen.value;
}

function selectOption(option) {
	selectedCategory.value = option.value;
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
