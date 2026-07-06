<template>
	<div
		class="flex items-center gap-1.5 h-[32px] rounded-lg border border-outline-variant bg-surface px-2.5 focus-within:ring-0 focus-within:outline-none"
	>
		<span
			class="material-symbols-outlined text-[16px] leading-none shrink-0 text-on-surface-variant"
		>
			search
		</span>

		<input
			:value="modelValue"
			:type="type"
			:placeholder="placeholder"
			class="w-full h-full bg-transparent text-[13px] leading-none text-on-surface outline-none border-none ring-0 focus:outline-none focus:ring-0 focus:border-none"
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
