<template>
	<section class="w-full px-4 py-3 space-y-2">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<BookingsViewSwitcher
				:modelValue="selectedView"
				:views="views"
				@update:modelValue="$emit('update:view', $event)"
			/>
			<div
				v-if="selectedView === 'bookings' && summary"
				class="flex items-center gap-2 flex-wrap"
			>
				<div class="bg-surface-container-high px-4 py-2 rounded-xl min-w-[80px]">
					<p class="text-label-sm text-outline">Total</p>
					<p class="text-headline-sm font-bold text-primary">{{ summary.total }}</p>
				</div>
				<div class="bg-surface-container-high px-4 py-2 rounded-xl min-w-[80px]">
					<p class="text-label-sm text-outline">Pending</p>
					<p class="text-headline-sm font-bold text-tertiary">
						{{ summary.pendingPayment }}
					</p>
				</div>
				<div class="bg-surface-container-high px-4 py-2 rounded-xl min-w-[80px]">
					<p class="text-label-sm text-outline">Checked In</p>
					<p class="text-headline-sm font-bold text-secondary">
						{{ summary.checkedIn }}
					</p>
				</div>
			</div>
			<AppointmentMetricsStrip
				v-else-if="selectedView === 'appointments'"
				:metrics="metrics"
			/>
		</div>

		<div class="flex flex-wrap items-center gap-2">
			<BookingSearchBar
				:modelValue="filters.searchText"
				placeholder="Search booking ID"
				class="min-w-[180px] max-w-[240px] flex-1"
				@update:modelValue="$emit('update:searchText', $event)"
			/>
			<BookingSearchBar
				:modelValue="filters.customerQuery"
				placeholder="Search guest"
				class="min-w-[150px] max-w-[200px] flex-1"
				@update:modelValue="$emit('update:customerQuery', $event)"
			/>
			<select
				:value="filters.statuses[0] || ''"
				class="h-[32px] rounded-lg border border-outline-variant bg-surface px-2.5 py-1.5 text-[12px] text-on-surface min-w-[120px]"
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
				class="h-[32px] rounded-lg border border-outline-variant bg-surface px-2.5 py-1.5 text-[12px] text-on-surface min-w-[120px]"
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
				class="h-[32px] rounded-lg border border-outline-variant bg-surface px-2.5 py-1.5 text-[12px] text-on-surface"
				@input="$emit('update:fromDate', $event.target.value)"
			/>
			<input
				type="date"
				:value="filters.toDate"
				class="h-[32px] rounded-lg border border-outline-variant bg-surface px-2.5 py-1.5 text-[12px] text-on-surface"
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
	summary: { type: Object, default: null },
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
