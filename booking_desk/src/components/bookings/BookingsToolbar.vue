<template>
	<section class="w-full px-4 py-3 space-y-3">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<BookingsViewSwitcher
				:modelValue="selectedView"
				:views="views"
				@update:modelValue="$emit('update:view', $event)"
			/>
			<AppointmentMetricsStrip
				v-if="selectedView === 'appointments'"
				:metrics="metrics"
				class="ml-4"
			/>
		</div>
		<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-6 gap-3">
			<BookingSearchBar
				:modelValue="filters.searchText"
				placeholder="Search booking ID or appointments"
				@update:modelValue="$emit('update:searchText', $event)"
			/>
			<BookingSearchBar
				:modelValue="filters.customerQuery"
				placeholder="Search guest"
				@update:modelValue="$emit('update:customerQuery', $event)"
			/>
			<select
				:value="filters.statuses[0] || ''"
				class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[13px]"
				@change="$emit('update:status', $event.target.value)"
			>
				<option value="">All statuses</option>
				<option v-for="status in statusOptions" :key="status" :value="status">
					{{ status }}
				</option>
			</select>
			<select
				v-if="showPaymentStatus"
				:value="filters.paymentStatuses?.[0] || ''"
				class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[13px]"
				@change="$emit('update:paymentStatus', $event.target.value)"
			>
				<option value="">All payments</option>
				<option v-for="status in paymentStatusOptions" :key="status" :value="status">
					{{ status }}
				</option>
			</select>
			<input
				type="date"
				:value="filters.fromDate"
				class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[13px]"
				@input="$emit('update:fromDate', $event.target.value)"
			/>
			<input
				type="date"
				:value="filters.toDate"
				class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[13px]"
				@input="$emit('update:toDate', $event.target.value)"
			/>
		</div>
	</section>
</template>

<script setup>
import BookingSearchBar from "@/components/bookings/BookingSearchBar.vue";
import BookingsViewSwitcher from "@/components/bookings/BookingsViewSwitcher.vue";
import AppointmentMetricsStrip from "@/components/bookings/appointments/AppointmentMetricsStrip.vue";

defineProps({
	filters: { type: Object, required: true },
	selectedView: { type: String, required: true },
	statusOptions: { type: Array, default: () => [] },
	paymentStatusOptions: { type: Array, default: () => [] },
	views: { type: Array, default: () => [] },
	metrics: { type: Object, default: () => ({}) },
	showPaymentStatus: { type: Boolean, default: true },
});

defineEmits([
	"update:view",
	"update:searchText",
	"update:customerQuery",
	"update:status",
	"update:paymentStatus",
	"update:fromDate",
	"update:toDate",
	"quick-booking",
]);
</script>
