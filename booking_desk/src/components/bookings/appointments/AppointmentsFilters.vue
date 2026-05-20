<template>
	<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-6 gap-2">
		<input
			class="px-3 py-2 bg-surface-container-lowest border border-outline-variant rounded-lg text-sm"
			placeholder="Search appointments"
			:value="filters.searchText"
			@input="$emit('update:searchText', $event.target.value)"
		/>
		<input
			class="px-3 py-2 bg-surface-container-lowest border border-outline-variant rounded-lg text-sm"
			placeholder="Customer"
			:value="filters.customerQuery"
			@input="$emit('update:customerQuery', $event.target.value)"
		/>
		<input
			class="px-3 py-2 bg-surface-container-lowest border border-outline-variant rounded-lg text-sm"
			placeholder="Booking Ref"
			:value="filters.bookingReference"
			@input="$emit('update:bookingReference', $event.target.value)"
		/>
		<select
			class="px-3 py-2 bg-surface-container-lowest border border-outline-variant rounded-lg text-sm"
			:value="filters.statuses[0] || ''"
			@change="$emit('update:status', $event.target.value)"
		>
			<option value="">All Statuses</option>
			<option v-for="status in statusOptions" :key="status" :value="status">
				{{ status }}
			</option>
		</select>
		<select
			class="px-3 py-2 bg-surface-container-lowest border border-outline-variant rounded-lg text-sm"
			:value="filters.provider"
			@change="$emit('update:provider', $event.target.value)"
		>
			<option value="">All Providers</option>
			<option v-for="provider in providerOptions" :key="provider" :value="provider">
				{{ provider }}
			</option>
		</select>
		<div class="flex gap-2">
			<input
				type="date"
				class="w-full px-3 py-2 bg-surface-container-lowest border border-outline-variant rounded-lg text-sm"
				:value="filters.fromDate"
				@change="$emit('update:fromDate', $event.target.value)"
			/>
			<input
				type="date"
				class="w-full px-3 py-2 bg-surface-container-lowest border border-outline-variant rounded-lg text-sm"
				:value="filters.toDate"
				@change="$emit('update:toDate', $event.target.value)"
			/>
		</div>
	</div>
</template>

<script setup>
defineProps({
	filters: { type: Object, required: true },
	providerOptions: { type: Array, default: () => [] },
	statusOptions: { type: Array, default: () => [] },
});

defineEmits([
	"update:searchText",
	"update:customerQuery",
	"update:bookingReference",
	"update:status",
	"update:provider",
	"update:fromDate",
	"update:toDate",
]);
</script>
