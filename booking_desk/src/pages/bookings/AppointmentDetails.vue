<template>
	<div class="h-full flex flex-col bg-background text-on-surface overflow-hidden">
		<main class="flex-1 min-w-0 px-4 pb-4 overflow-y-auto">
			<div class="max-w-[1360px] mx-auto w-full space-y-4 pt-4">
				<AppointmentDetailsLoadingState v-if="isLoading" />
				<AppointmentDetailsEmptyState
					v-else-if="error || !hasAppointment"
					:message="error"
					@retry="retry"
				/>
				<template v-else>
					<AppointmentDetailsHeader
						:appointment="appointment"
						:financial-summary="financialSummary"
						:actions="actionState"
						:busy="isSubmittingAction"
						@back="goBack"
						@check-in="checkIn"
						@start="startAppointment"
						@complete="completeAppointment"
					/>

					<div class="grid grid-cols-1 lg:grid-cols-12 gap-4 xl:gap-6">
						<div class="lg:col-span-8 space-y-4 xl:space-y-6">
							<div class="grid grid-cols-1 md:grid-cols-2 gap-4 xl:gap-6">
								<AppointmentServiceCard :appointment="appointment" />
								<AppointmentGuestCard :appointment="appointment" />
							</div>
							<AppointmentScheduleCard
								:appointment="appointment"
								@reschedule="openReschedulePanel"
								@reassign-provider="handleReassignProvider"
							/>
							<section
								v-if="isReschedulePanelOpen"
								class="rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-4 space-y-3"
							>
								<div class="flex items-center justify-between gap-3">
									<div>
										<p
											class="text-[11px] font-semibold uppercase tracking-wider text-outline"
										>
											Reschedule
										</p>
										<h3 class="text-sm font-semibold text-on-surface">
											Pick a new slot
										</h3>
									</div>
									<button
										type="button"
										class="px-3 py-1.5 rounded-full border border-outline-variant text-on-surface-variant hover:bg-surface-container-high text-xs"
										@click="closeReschedulePanel"
									>
										Close
									</button>
								</div>
								<AppointmentAvailabilityPanel
									:dates="dates"
									:slots="slots"
									:selected-date="selectedDate"
									:selected-slot-id="selectedSlotId"
									:selected-slot="selectedSlot"
									:busy="isSubmittingAction || isLoadingAvailability"
									@select-date="selectDate"
									@select-slot="selectSlot"
									@apply-slot="applySelectedSlot"
								/>
							</section>
							<AppointmentTimelinePanel :timeline="timeline" />
						</div>
						<div class="lg:col-span-4 space-y-4 xl:space-y-6">
							<AppointmentFinancialCard
								:appointment="appointment"
								:currency="financialSummary.currency"
								:total-amount="financialSummary.totalAmount"
								:paid-amount="financialSummary.paidAmount"
								:outstanding-amount="financialSummary.outstandingAmount"
								:payment-count="payments.length"
							/>
							<AppointmentBookingContextCard
								:booking="booking"
								:appointment="appointment"
								@open-booking="openBooking"
							/>
							<AppointmentAlertsPanel :alerts="alerts" />
							<AppointmentActionsPanel
								:actions="actionState"
								:busy="isSubmittingAction"
								@check-in="checkIn"
								@start="startAppointment"
								@complete="completeAppointment"
								@reschedule="openReschedulePanel"
								@reassign-provider="handleReassignProvider"
								@cancel="cancelAppointment"
							/>
						</div>
					</div>
				</template>
			</div>
		</main>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAppointmentDetails } from "@/composables/appointment-details/useAppointmentDetails";
import { useAppointmentActions } from "@/composables/appointment-details/useAppointmentActions";
import { useAppointmentScheduling } from "@/composables/appointment-details/useAppointmentScheduling";
import AppointmentDetailsLoadingState from "@/components/appointment-details/AppointmentDetailsLoadingState.vue";
import AppointmentDetailsEmptyState from "@/components/appointment-details/AppointmentDetailsEmptyState.vue";
import AppointmentDetailsHeader from "@/components/appointment-details/AppointmentDetailsHeader.vue";
import AppointmentServiceCard from "@/components/appointment-details/AppointmentServiceCard.vue";
import AppointmentGuestCard from "@/components/appointment-details/AppointmentGuestCard.vue";
import AppointmentScheduleCard from "@/components/appointment-details/AppointmentScheduleCard.vue";
import AppointmentAvailabilityPanel from "@/components/appointment-details/AppointmentAvailabilityPanel.vue";
import AppointmentTimelinePanel from "@/components/appointment-details/AppointmentTimelinePanel.vue";
import AppointmentFinancialCard from "@/components/appointment-details/AppointmentFinancialCard.vue";
import AppointmentBookingContextCard from "@/components/appointment-details/AppointmentBookingContextCard.vue";
import AppointmentAlertsPanel from "@/components/appointment-details/AppointmentAlertsPanel.vue";
import AppointmentActionsPanel from "@/components/appointment-details/AppointmentActionsPanel.vue";

const route = useRoute();
const router = useRouter();
const appointmentId = computed(() => String(route.params.appointmentId || ""));
const isReschedulePanelOpen = ref(false);

const {
	appointment,
	booking,
	payments,
	timeline,
	alerts,
	isLoading,
	isLoadingAvailability,
	isSubmittingAction,
	error,
	hasAppointment,
	financialSummary,
	actionState,
	retry,
} = useAppointmentDetails(appointmentId);

const {
	dates,
	slots,
	selectedDate,
	selectedSlotId,
	selectedSlot,
	selectDate,
	selectSlot,
	applySelectedSlot: applySelectedSlotAction,
} = useAppointmentScheduling();

const { checkIn, start, complete, cancel, reassignProvider } = useAppointmentActions();

const goBack = () => {
	if (appointment.value.bookingId) {
		router.push({
			name: "BookingDetails",
			params: { bookingId: appointment.value.bookingId },
		});
		return;
	}
	router.push({ name: "Bookings" });
};

const openBooking = () => {
	if (!appointment.value.bookingId) {
		return;
	}
	router.push({ name: "BookingDetails", params: { bookingId: appointment.value.bookingId } });
};

const openReschedulePanel = () => {
	isReschedulePanelOpen.value = true;
};

const closeReschedulePanel = () => {
	isReschedulePanelOpen.value = false;
};

const applySelectedSlot = async () => {
	const response = await applySelectedSlotAction();
	const nextAppointmentId = response?.nextAppointmentId || response?.appointment?.appointmentId;
	if (nextAppointmentId && nextAppointmentId !== appointmentId.value) {
		router.replace({
			name: "AppointmentDetails",
			params: { appointmentId: nextAppointmentId },
		});
		return;
	}
	closeReschedulePanel();
};

const startAppointment = async () => {
	await start();
};

const completeAppointment = async () => {
	await complete();
};

const cancelAppointment = async () => {
	await cancel();
};

const handleReassignProvider = async () => {
	await reassignProvider(
		selectedSlot.value?.providers?.[0]?.provider || appointment.value.provider
	);
};
</script>
