<template>
	<div class="h-full flex flex-col bg-background text-on-surface overflow-hidden">
		<main class="flex-1 min-w-0 px-4 pb-4 overflow-y-auto space-y-4">
			<div class="max-w-[1200px] mx-auto w-full space-y-4 pt-4">
				<BookingDetailsLoadingState v-if="isLoading" />
				<BookingDetailsEmptyState v-else-if="error || !hasBooking" @retry="retry" />
				<template v-else>
					<BookingHeader :booking="booking" :metrics="summaryMetrics" />
					<div class="grid grid-cols-1 lg:grid-cols-12 gap-4 xl:gap-6">
						<div class="lg:col-span-9 space-y-4 xl:space-y-6">
							<div class="grid grid-cols-1 md:grid-cols-2 gap-4 xl:gap-6">
								<BookingCustomerCard :booking="booking" />
								<BookingMetricsCard
									:booking="booking"
									:currency="booking.currency"
								/>
							</div>
							<OperationalAlertsPanel
								v-if="booking.alerts?.length"
								:alerts="booking.alerts"
							/>
							<AppointmentsWorkspace
								:appointments="booking.appointments"
								:currency="booking.currency"
								@open-appointment="openAppointment"
								@appointment-action="handleAppointmentAction"
							/>
						</div>
						<div class="lg:col-span-3 space-y-4 xl:space-y-6">
							<BookingOperationalSidebar
								:financial-summary="financialSummary"
								:currency="booking.currency"
								:alerts="booking.alerts"
								@collect-payment="collectPayment(booking)"
								@add-appointment="addAppointment(booking)"
								@reschedule-booking="rescheduleBooking(booking)"
							/>
						</div>
					</div>
				</template>
			</div>
		</main>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useBookingDetails } from "@/composables/booking-details/useBookingDetails";
import { useBookingOperations } from "@/composables/booking-details/useBookingOperations";
import BookingDetailsEmptyState from "@/components/booking-details/BookingDetailsEmptyState.vue";
import BookingDetailsLoadingState from "@/components/booking-details/BookingDetailsLoadingState.vue";
import BookingHeader from "@/components/booking-details/BookingHeader.vue";
import BookingCustomerCard from "@/components/booking-details/BookingCustomerCard.vue";
import BookingMetricsCard from "@/components/booking-details/BookingMetricsCard.vue";
import BookingOperationalSidebar from "@/components/booking-details/BookingOperationalSidebar.vue";
import AppointmentsWorkspace from "@/components/booking-details/AppointmentsWorkspace.vue";
import OperationalAlertsPanel from "@/components/booking-details/OperationalAlertsPanel.vue";

const route = useRoute();
const bookingId = computed(() => String(route.params.bookingId || ""));
const { booking, isLoading, error, hasBooking, financialSummary, summaryMetrics, retry } =
	useBookingDetails(bookingId);
const { openAppointment, collectPayment, addAppointment, rescheduleBooking, cancelAppointment } =
	useBookingOperations();

const handleAppointmentAction = (action, appointment) => {
	if (action === "start") {
		openAppointment(appointment, booking.value);
		return;
	}

	if (action === "cancel") {
		cancelAppointment(appointment, booking.value);
	}
};
</script>
