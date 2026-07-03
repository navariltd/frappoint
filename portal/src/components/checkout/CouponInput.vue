<template>
	<div class="space-y-2">
		<label class="text-label-md font-semibold text-on-surface">Promo Code</label>
		<div class="flex gap-2">
			<input
				class="flex-1 px-4 py-3 rounded-xl border border-outline-variant bg-surface text-body-md outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
				:disabled="disabled || loading"
				:value="modelValue"
				placeholder="Enter coupon code"
				type="text"
				@input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
				@keyup.enter="$emit('apply')"
			/>
			<button
				class="px-4 py-3 rounded-xl bg-primary text-on-primary font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
				:disabled="disabled || loading || !modelValue"
				type="button"
				@click="$emit('apply')"
			>
				<span v-if="loading">Applying...</span>
				<span v-else>Apply</span>
			</button>
		</div>
	</div>
</template>

<script setup lang="ts">
defineProps<{
	modelValue: string;
	loading?: boolean;
	disabled?: boolean;
}>();

defineEmits<{
	"update:modelValue": [value: string];
	apply: [];
}>();
</script>
