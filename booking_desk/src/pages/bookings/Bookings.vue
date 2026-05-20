<template>
	<div class="h-full flex flex-col bg-background text-on-surface overflow-hidden">
		<div class="flex-1 min-h-0 flex overflow-hidden">
			<main class="flex-1 min-w-0 px-4 pb-4 overflow-y-auto space-y-4">
				<div class="sticky top-0 z-20 -mx-4 bg-white pb-2">
					<BookingsToolbar
						:filters="filters"
						:selectedView="selectedView"
						:statusOptions="statusOptions"
						:paymentStatusOptions="paymentStatusOptions"
						:views="views"
						@update:view="onViewChange"
						@update:searchText="onSearchTextChange"
						@update:customerQuery="onCustomerQueryChange"
						@update:status="onStatusChange"
						@update:paymentStatus="onPaymentStatusChange"
						@update:fromDate="onFromDateChange"
						@update:toDate="onToDateChange"
					/>
				</div>

				<div
					v-if="error"
					class="rounded-lg border border-error-container bg-error-container/30 px-4 py-3"
				>
					<p class="text-[12px] text-on-surface">{{ error }}</p>
					<button class="mt-2 text-[12px] font-semibold text-primary" @click="retry">
						Retry
					</button>
				</div>

				<template v-if="isBookingsView">
					<BookingLoadingState v-if="isLoading" />
					<BookingEmptyState
						v-else-if="!hasBookings"
						@quick-booking="goToQuickBooking"
					/>
					<BookingCardGrid
						v-else
						:bookings="bookings"
						@open="openBooking"
						@collect="collectPayment"
						@checkin="checkIn"
						@reschedule="reschedule"
						@cancel="cancelBooking"
					/>
				</template>

				<AppointmentsView v-else-if="selectedView === BOOKING_VIEWS.APPOINTMENTS" />

				<div
					v-else
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-6 text-[13px] text-on-surface-variant"
				>
					{{ selectedView }} workspace is coming next. Bookings view is fully
					operational.
				</div>
			</main>

			<div
				v-if="isBookingsView"
				class="hidden xl:flex p-4 border-l border-outline-variant bg-surface min-h-0"
			>
				<BookingOperationalSidebar
					:summary="summary"
					:pendingPaymentBookings="pendingPaymentBookings"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import BookingCardGrid from "@/components/bookings/BookingCardGrid.vue";
import BookingEmptyState from "@/components/bookings/BookingEmptyState.vue";
import BookingLoadingState from "@/components/bookings/BookingLoadingState.vue";
import BookingOperationalSidebar from "@/components/bookings/BookingOperationalSidebar.vue";
import BookingsToolbar from "@/components/bookings/BookingsToolbar.vue";
import AppointmentsView from "@/components/bookings/views/AppointmentsView.vue";
import { useBookingActions } from "@/composables/bookings/useBookingActions";
import { useBookingFilters } from "@/composables/bookings/useBookingFilters";
import { useBookings } from "@/composables/bookings/useBookings";
import { useAppointments } from "@/composables/bookings/useAppointments";
import { BOOKING_VIEWS } from "@/types/bookings";

const router = useRouter();

const {
	bookings,
	selectedView,
	filters,
	isLoading,
	error,
	isBookingsView,
	summary,
	hasBookings,
	statusOptions,
	paymentStatusOptions,
	retry,
	setView,
} = useBookings();

// Appointments workspace store
const {
	filters: appointmentsFilters,
	updateFilters: updateAppointmentsFilters,
	resetFilters: resetAppointmentsFilters,
	retry: retryAppointments,
} = useAppointments();

const {
	updateSearchText,
	updateCustomerQuery,
	updateStatuses,
	updatePaymentStatuses,
	updateDateRange,
	applyFilters,
} = useBookingFilters();

const { openBooking, collectPayment, checkIn, reschedule, cancelBooking } = useBookingActions();

const pendingPaymentBookings = computed(() =>
	bookings.value.filter((booking) => booking.paymentStatus !== "Paid").slice(0, 8)
);

const views = [
	{ value: BOOKING_VIEWS.BOOKINGS, label: "Bookings" },
	{ value: BOOKING_VIEWS.APPOINTMENTS, label: "Appointments" },
	{ value: BOOKING_VIEWS.CALENDAR, label: "Calendar" },
];

let filtersDebounceTimer;

function triggerFilterApplyDebounced(delay = 250) {
	clearTimeout(filtersDebounceTimer);
	filtersDebounceTimer = setTimeout(() => {
		applyFilters();
	}, delay);
}

function onViewChange(view) {
	setView(view);
}

function onSearchTextChange(value) {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		updateAppointmentsFilters({ searchText: value }, { debounceMs: 0 });
		// Debounce fetch for appointments
		clearTimeout(filtersDebounceTimer);
		filtersDebounceTimer = setTimeout(() => {
			updateAppointmentsFilters({}, { debounceMs: 0 });
		}, 250);
	} else {
		updateSearchText(value);
		triggerFilterApplyDebounced();
	}
}

function onCustomerQueryChange(value) {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		updateAppointmentsFilters({ customerQuery: value }, { debounceMs: 0 });
		clearTimeout(filtersDebounceTimer);
		filtersDebounceTimer = setTimeout(() => {
			updateAppointmentsFilters({}, { debounceMs: 0 });
		}, 250);
	} else {
		updateCustomerQuery(value);
		triggerFilterApplyDebounced();
	}
}

function onStatusChange(value) {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		updateAppointmentsFilters({ statuses: value ? [value] : [] }, { debounceMs: 0 });
	} else {
		updateStatuses(value ? [value] : []);
		applyFilters();
	}
}

function onPaymentStatusChange(value) {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		updateAppointmentsFilters({ paymentStatuses: value ? [value] : [] }, { debounceMs: 0 });
	} else {
		updatePaymentStatuses(value ? [value] : []);
		applyFilters();
	}
}

function onFromDateChange(value) {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		updateAppointmentsFilters(
			{ fromDate: value, toDate: appointmentsFilters.value.toDate },
			{ debounceMs: 0 }
		);
	} else {
		updateDateRange({ fromDate: value, toDate: filters.value.toDate });
		applyFilters();
	}
}

function onToDateChange(value) {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		updateAppointmentsFilters(
			{ fromDate: appointmentsFilters.value.fromDate, toDate: value },
			{ debounceMs: 0 }
		);
	} else {
		updateDateRange({ fromDate: filters.value.fromDate, toDate: value });
		applyFilters();
	}
}

onBeforeUnmount(() => {
	clearTimeout(filtersDebounceTimer);
});
</script>
