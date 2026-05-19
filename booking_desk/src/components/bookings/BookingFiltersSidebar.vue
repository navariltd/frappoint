<template>
	<aside
		class="hidden xl:block w-72 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-4"
	>
		<h3 class="text-[13px] font-semibold text-on-surface">Operational Filters</h3>
		<div class="text-[12px] text-on-surface-variant space-y-1">
			<p>Status: {{ (filters.statuses || []).join(", ") || "All" }}</p>
			<p>Payment: {{ (filters.paymentStatuses || []).join(", ") || "All" }}</p>
			<p>Date: {{ filters.fromDate || "-" }} to {{ filters.toDate || "-" }}</p>
		</div>
		<button
			type="button"
			class="w-full rounded-lg border border-outline-variant px-3 py-2 text-[12px] font-semibold"
			@click="$emit('reset')"
		>
			Reset Filters
		</button>
	</aside>
</template>

<script setup>
defineProps({ filters: { type: Object, required: true } });
defineEmits(["reset"]);
</script>
