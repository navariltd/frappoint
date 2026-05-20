<template>
	<div class="h-full flex flex-col bg-background text-on-surface overflow-hidden">
		<main class="flex-1 min-w-0 px-4 pb-5 overflow-y-auto">
			<div class="max-w-[1320px] mx-auto w-full space-y-4 pt-4 lg:pt-5">
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
						@pause="pauseAppointment"
						@resume="resumeAppointment"
						@complete="completeAppointment"
					/>

					<div class="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-5 xl:gap-6">
						<div class="lg:col-span-8 space-y-4 lg:space-y-5">
							<div class="grid grid-cols-1 md:grid-cols-2 gap-4 lg:gap-5">
								<AppointmentServiceCard :appointment="appointment" />
								<AppointmentGuestCard :appointment="appointment" />
							</div>
							<AppointmentScheduleCard
								:appointment="appointment"
								:actions="actionState"
								@reschedule="openReschedulePanel"
								@reassign-provider="handleReassignProvider"
							/>
							<section
								v-if="isReschedulePanelOpen"
								class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 space-y-4"
							>
								<div class="flex items-center justify-between gap-3">
									<div>
										<p
											class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline"
										>
											Reschedule
										</p>
										<h3
											class="text-sm font-semibold text-on-surface tracking-tight"
										>
											Pick a new slot
										</h3>
									</div>
									<button
										type="button"
										class="px-3 py-1.5 rounded-md border border-outline-variant/60 text-on-surface-variant hover:bg-surface-container-high hover:border-outline transition-colors text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
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
							<AppointmentTimelinePanel
								:segments="timelineSegments"
								:active-session="activeSession"
								:current-duration="currentDuration"
								:total-pause-seconds="totalPauseSeconds"
							/>
						</div>
						<div
							class="lg:col-span-4 space-y-4 lg:space-y-5 lg:sticky lg:top-4 self-start"
						>
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
								@pause="pauseAppointment"
								@resume="resumeAppointment"
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
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";
import { useAppointmentDetails } from "@/composables/appointment-details/useAppointmentDetails";
import { useAppointmentActions } from "@/composables/appointment-details/useAppointmentActions";
import { useAppointmentScheduling } from "@/composables/appointment-details/useAppointmentScheduling";
import { useAppointmentEventLogsStore } from "@/stores/appointmentEventLogs.store";
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
const eventLogsStore = useAppointmentEventLogsStore();
const { timelineSegments, activeSession, currentDuration, totalPauseSeconds } =
	storeToRefs(eventLogsStore);

const {
	appointment,
	booking,
	payments,
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

const { checkIn, start, pause, resume, complete, cancel, reassignProvider } =
	useAppointmentActions();

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

const pauseAppointment = async () => {
	await pause();
};

const resumeAppointment = async () => {
	await resume();
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
