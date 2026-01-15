<template>
	<div class="flex gap-2 w-full">
		<button
			v-for="button in buttons"
			:key="button.value"
			:class="[
				'text-sm font-medium px-4 py-2 rounded transition-all duration-200',
				modelValue === button.value
					? 'bg-blue-600 text-white shadow-md'
					: 'bg-gray-200 text-gray-700 hover:bg-gray-300',
			]"
			@click="$emit('update:modelValue', button.value)"
		>
			{{ button.label }}
		</button>
	</div>
</template>

<script setup>
defineProps({
	buttons: {
		type: Array,
		required: true,
	},
	modelValue: {
		type: String,
		required: true,
	},
});

defineEmits(["update:modelValue"]);
</script>
