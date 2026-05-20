<template>
	<section class="mb-6 space-y-4">
		<AppointmentMetricsStrip :metrics="metrics" />
		<div class="rounded-xl border border-outline-variant bg-surface-container-lowest p-3">
			<AppointmentsFilters
				:filters="filters"
				:providerOptions="providerOptions"
				:statusOptions="statusOptions"
				@update:searchText="$emit('update:searchText', $event)"
				@update:customerQuery="$emit('update:customerQuery', $event)"
				@update:bookingReference="$emit('update:bookingReference', $event)"
				@update:status="$emit('update:status', $event)"
				@update:provider="$emit('update:provider', $event)"
				@update:fromDate="$emit('update:fromDate', $event)"
				@update:toDate="$emit('update:toDate', $event)"
			/>
		</div>
	</section>
</template>

<script setup>
import AppointmentMetricsStrip from "@/components/bookings/appointments/AppointmentMetricsStrip.vue";
import AppointmentsFilters from "@/components/bookings/appointments/AppointmentsFilters.vue";

defineProps({
	metrics: { type: Object, required: true },
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
