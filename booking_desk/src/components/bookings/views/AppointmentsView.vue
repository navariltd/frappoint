<template>
	<section class="space-y-4">
		<div
			v-if="error"
			class="rounded-lg border border-error-container bg-error-container/30 px-4 py-3"
		>
			<p class="text-[12px] text-on-surface">{{ error }}</p>
			<button class="mt-2 text-[12px] font-semibold text-primary" @click="retry">
				Retry
			</button>
		</div>

		<LoadingAppointmentsState v-if="isLoading" />
		<EmptyAppointmentsState v-else-if="!hasAppointments" @reset="onResetFilters" />
		<AppointmentsListView
			v-else
			:appointments="appointments"
			@open="onOpenAppointment"
			@checkin="onCheckInAppointment"
		/>
	</section>
</template>

<script setup>
import { onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
// Removed AppointmentsToolbar import
import AppointmentsListView from "@/components/bookings/appointments/AppointmentsListView.vue";
import EmptyAppointmentsState from "@/components/bookings/appointments/EmptyAppointmentsState.vue";
import LoadingAppointmentsState from "@/components/bookings/appointments/LoadingAppointmentsState.vue";
import { useAppointments } from "@/composables/bookings/useAppointments";

const router = useRouter();

const {
	appointments,
	metrics,
	filters,
	isLoading,
	error,
	hasAppointments,
	providerOptions,
	statusOptions,
	updateFilters,
	resetFilters,
	retry,
} = useAppointments();

let filtersDebounceTimer;

function triggerFilterApplyDebounced(delay = 250) {
	clearTimeout(filtersDebounceTimer);
	filtersDebounceTimer = setTimeout(() => {
		updateFilters({}, { debounceMs: 0 });
	}, delay);
}

function onSearchTextChange(value) {
	updateFilters({ searchText: value }, { debounceMs: 0 });
	triggerFilterApplyDebounced();
}

function onCustomerQueryChange(value) {
	updateFilters({ customerQuery: value }, { debounceMs: 0 });
	triggerFilterApplyDebounced();
}

function onBookingReferenceChange(value) {
	updateFilters({ bookingReference: value }, { debounceMs: 0 });
	triggerFilterApplyDebounced();
}

function onStatusChange(value) {
	updateFilters({ statuses: value ? [value] : [] }, { debounceMs: 0 });
}

function onProviderChange(value) {
	updateFilters({ provider: value || "" }, { debounceMs: 0 });
}

function onFromDateChange(value) {
	updateFilters({ fromDate: value || "" }, { debounceMs: 0 });
}

function onToDateChange(value) {
	updateFilters({ toDate: value || "" }, { debounceMs: 0 });
}

function onOpenAppointment(appointment) {
	router.push({
		name: "AppointmentDetails",
		params: { appointmentId: appointment.appointmentId },
		query: { source: "appointments-workspace" },
	});
}

function onCheckInAppointment(appointment) {
	onOpenAppointment(appointment);
}

function onResetFilters() {
	resetFilters();
	retry();
}

onBeforeUnmount(() => {
	clearTimeout(filtersDebounceTimer);
});
</script>
