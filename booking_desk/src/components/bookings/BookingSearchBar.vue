<template>
	<div
		class="flex items-center gap-2 rounded-lg border border-outline-variant bg-surface px-3 py-2"
	>
		<span class="material-symbols-outlined text-[18px] text-on-surface-variant">search</span>
		<input
			:value="modelValue"
			:type="type"
			:placeholder="placeholder"
			class="w-full bg-transparent text-[13px] text-on-surface outline-none"
			@input="$emit('update:modelValue', $event.target.value)"
		/>
	</div>
</template>

<script setup>
defineProps({
	modelValue: { type: String, default: "" },
	placeholder: { type: String, default: "Search" },
	type: { type: String, default: "text" },
});

defineEmits(["update:modelValue"]);
</script>
