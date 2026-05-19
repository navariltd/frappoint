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
						@quick-booking="goToQuickBooking"
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

				<div
					v-if="!isBookingsView"
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-6 text-[13px] text-on-surface-variant"
				>
					{{ selectedView }} workspace is coming next. Bookings view is fully
					operational.
				</div>

				<template v-else>
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
			</main>

			<div class="hidden xl:flex p-4 border-l border-outline-variant bg-surface min-h-0">
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
import { useBookingActions } from "@/composables/bookings/useBookingActions";
import { useBookingFilters } from "@/composables/bookings/useBookingFilters";
import { useBookings } from "@/composables/bookings/useBookings";
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

function goToQuickBooking() {
	router.push({ name: "Services" });
}

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
	updateSearchText(value);
	triggerFilterApplyDebounced();
}

function onCustomerQueryChange(value) {
	updateCustomerQuery(value);
	triggerFilterApplyDebounced();
}

function onStatusChange(value) {
	updateStatuses(value ? [value] : []);
	applyFilters();
}

function onPaymentStatusChange(value) {
	updatePaymentStatuses(value ? [value] : []);
	applyFilters();
}

function onFromDateChange(value) {
	updateDateRange({ fromDate: value, toDate: filters.value.toDate });
	applyFilters();
}

function onToDateChange(value) {
	updateDateRange({ fromDate: filters.value.fromDate, toDate: value });
	applyFilters();
}

onBeforeUnmount(() => {
	clearTimeout(filtersDebounceTimer);
});
</script>
