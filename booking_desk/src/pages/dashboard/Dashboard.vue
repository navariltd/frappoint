<template>
	<div class="min-h-full bg-surface-container-low p-4 md:p-6 space-y-6">
		<DashboardMetricsCards :cards="summaryCards" />

		<div class="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6 items-start">
			<div class="lg:col-span-8 space-y-4">
				<LiveResourceTimeline
					:providers="providers"
					:appointments="appointments"
					:selected-date="selectedDate"
					:panel-height-class="topPanelHeightClass"
					:view="view"
					:statuses="timelineStatuses"
					:loading="dashboardLoading"
					:error="dashboardError"
					@appointments-updated="onAppointmentsUpdated"
					@date-changed="onDateChanged"
					@view-changed="onViewChanged"
					@retry="retry"
					@appointment-selected="onTimelineAppointmentSelected"
				/>

				<AppointmentDetailsPanel
					:appointment="selectedTimelineAppointment"
					:providers="providers"
				/>
			</div>

			<aside class="lg:col-span-4 space-y-4">
				<LiveReceptionQueue
					:appointments="appointments"
					:providers="providers"
					:selected-date="selectedDate"
					:panel-height-class="topPanelHeightClass"
					@check-in="onQueueCheckIn"
					@start="onQueueStart"
					@view-details="onViewAppointment"
				/>

				<OccupancyOverview
					:providers="providers"
					:appointments="appointments"
					:selected-date="selectedDate"
					:panel-height-class="occupancyPanelHeightClass"
				/>
			</aside>
		</div>

		<RecentActivityFeed :appointments="appointments" :selected-date="selectedDate" />
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import AppointmentDetailsPanel from "@/components/dashboard/AppointmentDetailsPanel.vue";
import DashboardMetricsCards from "@/components/dashboard/DashboardMetricsCards.vue";
import LiveResourceTimeline from "@/components/dashboard/LiveResourceTimeline.vue";
import LiveReceptionQueue from "@/components/dashboard/LiveReceptionQueue.vue";
import OccupancyOverview from "@/components/dashboard/OccupancyOverview.vue";
import RecentActivityFeed from "@/components/dashboard/RecentActivityFeed.vue";
import { useDashboard } from "@/composables/dashboard/useDashboard";
import { useProviderTimeline } from "@/composables/dashboard/useProviderTimeline";

const router = useRouter();
const { summaryCards, isLoading: dashboardLoading, error: dashboardError, retry } = useDashboard();
const {
	providers,
	appointments,
	selectedDate,
	view,
	timelineStatuses,
	onAppointmentsUpdated,
	onDateChanged,
	onViewChanged,
} = useProviderTimeline();
const selectedTimelineAppointment = ref(null);
const topPanelHeightClass = computed(() =>
	providers.value.length > 6 ? "h-[34rem]" : "h-full min-h-[22rem]"
);
const occupancyPanelHeightClass = "h-[22rem]";

const updateAppointmentStatus = (appointmentId, nextStatus) => {
	const nextAppointments = appointments.value.map((item) => {
		if (item.id !== appointmentId) {
			return item;
		}
		return {
			...item,
			status: nextStatus,
		};
	});
	onAppointmentsUpdated(nextAppointments);
};

const onQueueCheckIn = (appointment) => {
	updateAppointmentStatus(appointment.id, "Checked In");
};

const onQueueStart = (appointment) => {
	updateAppointmentStatus(appointment.id, "Ongoing");
};

const onViewAppointment = (appointment) => {
	router.push({
		name: "AppointmentDetails",
		params: { appointmentId: appointment.id },
	});
};

const onTimelineAppointmentSelected = (appointment) => {
	selectedTimelineAppointment.value = appointment || null;
};
</script>
