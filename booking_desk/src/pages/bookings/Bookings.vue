<template>
	<div class="h-full flex flex-col bg-background text-on-surface overflow-hidden">
		<div class="flex-1 min-h-0 flex overflow-hidden">
			<main class="flex-1 min-w-0 px-4 pb-4 overflow-y-auto space-y-4">
				<div class="sticky top-0 z-20 -mx-4 bg-white pb-2">
					<BookingsToolbar
						:filters="toolbarFilters"
						:selectedView="selectedView"
						:statusOptions="toolbarStatusOptions"
						:paymentStatusOptions="toolbarPaymentStatusOptions"
						:showPaymentStatus="showPaymentStatus"
						:metrics="appointmentsMetrics"
						:summary="summary"
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
					v-if="activeWorkspaceError"
					class="rounded-lg border border-error-container bg-error-container/30 px-4 py-3"
				>
					<p class="text-[12px] text-on-surface">{{ activeWorkspaceError }}</p>
					<button
						class="mt-2 text-[12px] font-semibold text-primary"
						@click="retryActiveView"
					>
						Retry
					</button>
				</div>

				<template v-if="isBookingsView">
					<BookingLoadingState v-if="isLoading" />
					<BookingEmptyState v-else-if="!hasBookings" />
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
				<CalendarView
					v-else-if="selectedView === BOOKING_VIEWS.CALENDAR"
					@prev="onCalendarPrev"
					@next="onCalendarNext"
					@today="onCalendarToday"
					@changeView="onCalendarChangeView"
				/>
			</main>
		</div>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount } from "vue";
import { storeToRefs } from "pinia";
import BookingCardGrid from "@/components/bookings/BookingCardGrid.vue";
import BookingEmptyState from "@/components/bookings/BookingEmptyState.vue";
import BookingLoadingState from "@/components/bookings/BookingLoadingState.vue";
import BookingsToolbar from "@/components/bookings/BookingsToolbar.vue";
import AppointmentsView from "@/components/bookings/views/AppointmentsView.vue";
import CalendarView from "@/components/bookings/views/CalendarView.vue";
import { useBookingActions } from "@/composables/bookings/useBookingActions";
import { useBookingFilters } from "@/composables/bookings/useBookingFilters";
import { useBookings } from "@/composables/bookings/useBookings";
import { useCalendarWorkspace } from "@/composables/bookings/useCalendarWorkspace";
import { useAppointmentsStore } from "@/stores/appointments.store";
import { useCalendarStore } from "@/stores/calendar.store";
import { BOOKING_VIEWS } from "@/types/bookings";

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

const appointmentsStore = useAppointmentsStore();
const calendarStore = useCalendarStore();
const {
	filters: appointmentsFilters,
	statusOptions: appointmentsStatusOptions,
	paymentStatusOptions: appointmentsPaymentStatusOptions,
	metrics: appointmentsMetrics,
	error: appointmentsError,
} = storeToRefs(appointmentsStore);
const {
	filters: calendarFilters,
	statusOptions: calendarStatusOptions,
	error: calendarError,
} = storeToRefs(calendarStore);

const {
	updateSearchText,
	updateCustomerQuery,
	updateStatuses,
	updatePaymentStatuses,
	updateDateRange,
	applyFilters,
} = useBookingFilters();

const { openBooking, collectPayment, checkIn, reschedule, cancelBooking } = useBookingActions();

const { goPrev, goNext, goToday, setView: setCalendarView } = useCalendarWorkspace();

const views = [
	{ value: BOOKING_VIEWS.BOOKINGS, label: "Bookings" },
	{ value: BOOKING_VIEWS.APPOINTMENTS, label: "Appointments" },
	{ value: BOOKING_VIEWS.CALENDAR, label: "Calendar" },
];

const toolbarFilters = computed(() => {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		return appointmentsFilters.value;
	}
	if (selectedView.value === BOOKING_VIEWS.CALENDAR) {
		return calendarFilters.value;
	}
	return filters.value;
});

const toolbarStatusOptions = computed(() => {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		return appointmentsStatusOptions.value;
	}
	if (selectedView.value === BOOKING_VIEWS.CALENDAR) {
		return calendarStatusOptions.value;
	}
	return statusOptions.value;
});

const toolbarPaymentStatusOptions = computed(() => {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		return appointmentsPaymentStatusOptions.value;
	}
	return paymentStatusOptions.value;
});

const showPaymentStatus = computed(() => selectedView.value !== BOOKING_VIEWS.CALENDAR);

const activeWorkspaceError = computed(() => {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		return appointmentsError.value;
	}
	if (selectedView.value === BOOKING_VIEWS.CALENDAR) {
		return calendarError.value;
	}
	return error.value;
});

let filtersDebounceTimer;

function triggerFilterApplyDebounced(callback, delay = 250) {
	clearTimeout(filtersDebounceTimer);
	filtersDebounceTimer = setTimeout(() => {
		callback();
	}, delay);
}

function onViewChange(view) {
	setView(view);
}

function onSearchTextChange(value) {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		appointmentsStore.updateFilters({ searchText: value }, { debounceMs: 300 });
		return;
	}
	if (selectedView.value === BOOKING_VIEWS.CALENDAR) {
		calendarStore.updateFilters({ searchText: value }, { debounceMs: 300 });
		return;
	}
	updateSearchText(value);
	triggerFilterApplyDebounced(() => applyFilters());
}

function onCustomerQueryChange(value) {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		appointmentsStore.updateFilters({ customerQuery: value }, { debounceMs: 300 });
		return;
	}
	if (selectedView.value === BOOKING_VIEWS.CALENDAR) {
		calendarStore.updateFilters({ customerQuery: value }, { debounceMs: 300 });
		return;
	}
	updateCustomerQuery(value);
	triggerFilterApplyDebounced(() => applyFilters());
}

function onStatusChange(value) {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		appointmentsStore.updateFilters({ statuses: value ? [value] : [] }, { debounceMs: 0 });
		return;
	}
	if (selectedView.value === BOOKING_VIEWS.CALENDAR) {
		calendarStore.updateFilters({ statuses: value ? [value] : [] }, { debounceMs: 0 });
		return;
	}
	updateStatuses(value ? [value] : []);
	applyFilters();
}

function onPaymentStatusChange(value) {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		appointmentsStore.updateFilters(
			{ paymentStatuses: value ? [value] : [] },
			{ debounceMs: 0 }
		);
		return;
	}
	updatePaymentStatuses(value ? [value] : []);
	applyFilters();
}

function onFromDateChange(value) {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		appointmentsStore.updateFilters(
			{ fromDate: value, toDate: appointmentsFilters.value.toDate },
			{ debounceMs: 0 }
		);
		return;
	}
	if (selectedView.value === BOOKING_VIEWS.CALENDAR) {
		calendarStore.updateFilters(
			{ fromDate: value, toDate: calendarFilters.value.toDate },
			{ debounceMs: 0 }
		);
		return;
	}
	updateDateRange({ fromDate: value, toDate: filters.value.toDate });
	applyFilters();
}

function onToDateChange(value) {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		appointmentsStore.updateFilters(
			{ fromDate: appointmentsFilters.value.fromDate, toDate: value },
			{ debounceMs: 0 }
		);
		return;
	}
	if (selectedView.value === BOOKING_VIEWS.CALENDAR) {
		calendarStore.updateFilters(
			{ fromDate: calendarFilters.value.fromDate, toDate: value },
			{ debounceMs: 0 }
		);
		return;
	}
	updateDateRange({ fromDate: filters.value.fromDate, toDate: value });
	applyFilters();
}

function onCalendarPrev() {
	goPrev();
}

function onCalendarNext() {
	goNext();
}

function onCalendarToday() {
	goToday();
}

function onCalendarChangeView(view) {
	setCalendarView(view);
}

function retryActiveView() {
	if (selectedView.value === BOOKING_VIEWS.APPOINTMENTS) {
		appointmentsStore.retry();
		return;
	}
	if (selectedView.value === BOOKING_VIEWS.CALENDAR) {
		calendarStore.retry();
		return;
	}
	retry();
}

onBeforeUnmount(() => {
	clearTimeout(filtersDebounceTimer);
});
</script>
