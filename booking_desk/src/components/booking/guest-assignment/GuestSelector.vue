<template>
	<div class="space-y-2">
		<div class="flex items-center gap-2">
			<select
				class="flex-1 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px]"
				:value="modelValue"
				@change="$emit('select', $event.target.value)"
			>
				<option value="">Select existing guest</option>
				<option v-for="customer in customers" :key="customer.id" :value="customer.id">
					{{ customer.name }}
				</option>
			</select>
			<button
				type="button"
				class="rounded-lg border border-outline-variant px-3 py-2 text-[12px]"
				@click="$emit('quick-create')"
			>
				Quick Add
			</button>
			<button
				type="button"
				class="rounded-lg px-3 py-2 text-[12px] text-error"
				@click="$emit('clear')"
			>
				Clear
			</button>
		</div>
		<p class="text-[11px] text-on-surface-variant">
			{{ guestName || "No guest selected" }}
		</p>
	</div>
</template>

<script setup>
defineProps({
	modelValue: {
		type: String,
		default: "",
	},
	guestName: {
		type: String,
		default: "",
	},
	customers: {
		type: Array,
		default: () => [],
	},
});

defineEmits(["select", "quick-create", "clear"]);
</script>
