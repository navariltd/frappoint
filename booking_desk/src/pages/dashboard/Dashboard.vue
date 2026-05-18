<style>
.material-symbols-outlined {
	font-variation-settings: "FILL" 0, "wght" 400, "GRAD" 0, "opsz" 24;
}
.glass-card {
	background: rgba(255, 255, 255, 0.8);
	backdrop-filter: blur(8px);
	border: 1px solid #e5e5e1;
}
.scrollbar-hide::-webkit-scrollbar {
	display: none;
}
</style>

<template>
	<!-- Main Content Area -->
	<div class="p-6 space-y-6">
		<!-- Operational Summary Cards -->
		<section class="grid lg:grid-cols-6 gap-4 md:grid-cols-3">
			<OperationalSummaryCards v-for="card in summaryCards" :key="card.key" v-bind="card" />
		</section>

		<div class="grid grid-cols-12 gap-6">
			<!-- Live Operational Timeline (Dominant Focus) -->
			<div class="col-span-9 space-y-3">
				<div
					v-if="dashboardError"
					class="rounded-lg border border-error-container bg-error-container/30 px-3 py-2 text-[12px] text-on-surface flex items-center justify-between"
				>
					<span>{{ dashboardError }}</span>
					<button class="text-primary font-semibold" @click="retry">Retry</button>
				</div>
				<div v-if="dashboardLoading" class="text-[12px] text-on-surface-variant px-1">
					Loading dashboard data...
				</div>
				<ResourceTimeline
					title="Live Resource Timeline"
					:providers="providers"
					:appointments="appointments"
					:selectedDateValue="selectedDate"
					:defaultView="view"
					:statuses="timelineStatuses"
					@appointments-updated="onAppointmentsUpdated"
					@date-changed="onDateChanged"
					@view-changed="onViewChanged"
				/>
			</div>
			<!-- Check-in & Queue Panel -->
			<aside class="col-span-3 space-y-6">
				<section
					class="bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant p-4"
				>
					<div class="flex items-center justify-between mb-4">
						<h3 class="font-label-md text-label-md font-bold">Live Reception Queue</h3>
						<span
							class="bg-primary-container text-on-primary-container text-[10px] px-2 py-0.5 rounded-full font-bold"
							>3 GUESTS</span
						>
					</div>
					<div class="space-y-3">
						<!-- Queue Item 1 -->
						<div
							class="p-3 bg-surface rounded-xl border border-outline-variant flex flex-col gap-2"
						>
							<div class="flex justify-between items-start">
								<div>
									<p class="font-label-md text-label-md">Jane Smith</p>
									<p class="text-[10px] text-on-surface-variant">
										Arrived 5m ago •
										<span class="text-secondary font-bold">Checked in</span>
									</p>
								</div>
								<button class="text-primary material-symbols-outlined">
									more_vert
								</button>
							</div>
							<button
								class="w-full py-1.5 bg-primary text-on-primary rounded-lg text-[12px] font-bold"
							>
								Start Session
							</button>
						</div>
						<!-- Queue Item 2 -->
						<div
							class="p-3 bg-surface-container-low rounded-xl border border-outline-variant"
						>
							<div class="flex justify-between items-start">
								<div>
									<p class="font-label-md text-label-md text-on-surface-variant">
										Liam Hudson
									</p>
									<p class="text-[10px] text-on-surface-variant">
										Waiting in lounge
									</p>
								</div>
								<button
									class="px-2 py-1 bg-surface-container-lowest border border-outline-variant rounded-lg text-[10px] font-bold text-on-surface"
								>
									Check In
								</button>
							</div>
						</div>
						<!-- Queue Item 3 -->
						<div
							class="p-3 bg-secondary-container/20 rounded-xl border border-secondary-container/50"
						>
							<div class="flex justify-between items-start">
								<div>
									<p class="font-label-md text-label-md">Marcus Thorne</p>
									<p class="text-[10px] text-secondary font-bold">
										In-progress • Room 2
									</p>
								</div>
								<span
									class="material-symbols-outlined text-secondary text-sm"
									style="font-variation-settings: 'FILL' 1"
									>vital_signs</span
								>
							</div>
						</div>
					</div>
				</section>
				<!-- Walk-in availability widget -->
				<section
					class="bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant p-4"
				>
					<h3 class="font-label-md text-label-md font-bold mb-3">
						Walk-in Availability
					</h3>
					<div class="space-y-2">
						<div
							class="flex justify-between items-center p-2 rounded-lg bg-surface border border-outline-variant"
						>
							<span class="text-[12px] font-medium">Massage</span>
							<span
								class="text-[10px] px-2 py-0.5 bg-secondary-container text-on-secondary-container rounded-full font-bold"
								>2 SLOTS</span
							>
						</div>
						<div
							class="flex justify-between items-center p-2 rounded-lg bg-surface border border-outline-variant opacity-60"
						>
							<span class="text-[12px] font-medium">Facial</span>
							<span
								class="text-[10px] px-2 py-0.5 bg-error-container text-on-error-container rounded-full font-bold"
								>NONE</span
							>
						</div>
						<div
							class="flex justify-between items-center p-2 rounded-lg bg-surface border border-outline-variant"
						>
							<span class="text-[12px] font-medium">Yoga Class</span>
							<span
								class="text-[10px] px-2 py-0.5 bg-secondary-container text-on-secondary-container rounded-full font-bold"
								>1 SLOT</span
							>
						</div>
					</div>
				</section>
			</aside>
		</div>
		<!-- Bottom Section: Alerts & Recent Activity -->
		<div class="grid grid-cols-12 gap-6">
			<!-- Alerts -->
			<section
				class="col-span-5 bg-error-container/20 rounded-2xl border border-error-container p-5"
			>
				<div class="flex items-center gap-2 mb-4">
					<span
						class="material-symbols-outlined text-error"
						style="font-variation-settings: 'FILL' 1"
						>report</span
					>
					<h3 class="font-label-md text-label-md font-bold text-on-error-container">
						Action Required (2)
					</h3>
				</div>
				<div class="space-y-3">
					<div
						class="flex items-start gap-3 bg-white p-3 rounded-xl border border-error-container shadow-sm"
					>
						<div class="w-2 h-2 rounded-full bg-error mt-2"></div>
						<div class="flex-1">
							<p class="text-[12px] font-bold">Room 4 Double Booking</p>
							<p class="text-[11px] text-on-surface-variant">
								Dr. Aris V. and Lydia Moore assigned to Room 4 at 11:30 AM.
							</p>
						</div>
						<button class="text-primary text-[11px] font-bold underline">
							Resolve
						</button>
					</div>
					<div
						class="flex items-start gap-3 bg-white p-3 rounded-xl border border-error-container shadow-sm"
					>
						<div class="w-2 h-2 rounded-full bg-error mt-2"></div>
						<div class="flex-1">
							<p class="text-[12px] font-bold">Resource Alert</p>
							<p class="text-[11px] text-on-surface-variant">
								Lydia Moore is over 15 minutes delayed for next session.
							</p>
						</div>
						<button class="text-primary text-[11px] font-bold underline">
							Notify Guest
						</button>
					</div>
				</div>
			</section>
			<!-- Recent Activity -->
			<section
				class="col-span-7 bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant p-5"
			>
				<h3 class="font-label-md text-label-md font-bold mb-4">Recent Activity Feed</h3>
				<div class="space-y-4">
					<div
						class="flex items-center justify-between border-b border-outline-variant pb-2"
					>
						<div class="flex items-center gap-3">
							<span class="material-symbols-outlined text-secondary text-sm"
								>payments</span
							>
							<div>
								<p class="text-[12px] font-medium">
									Payment Processed - Sarah Jenkins
								</p>
								<p class="text-[10px] text-on-surface-variant">
									Deep Tissue (60m) • $120.00
								</p>
							</div>
						</div>
						<span class="text-[10px] text-on-surface-variant font-medium">2m ago</span>
					</div>
					<div
						class="flex items-center justify-between border-b border-outline-variant pb-2"
					>
						<div class="flex items-center gap-3">
							<span class="material-symbols-outlined text-primary text-sm"
								>login</span
							>
							<div>
								<p class="text-[12px] font-medium">Checked In - Jane Smith</p>
								<p class="text-[10px] text-on-surface-variant">
									Consultation with Dr. Marcus S.
								</p>
							</div>
						</div>
						<span class="text-[10px] text-on-surface-variant font-medium">5m ago</span>
					</div>
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-3">
							<span class="material-symbols-outlined text-tertiary text-sm"
								>event_repeat</span
							>
							<div>
								<p class="text-[12px] font-medium">Rescheduled - Liam Hudson</p>
								<p class="text-[10px] text-on-surface-variant">
									Moved from 10:00 to 11:15 AM
								</p>
							</div>
						</div>
						<span class="text-[10px] text-on-surface-variant font-medium"
							>14m ago</span
						>
					</div>
				</div>
			</section>
		</div>
	</div>
	<!-- Contextual FAB (Only for Home/Dashboard context) -->
	<button
		class="fixed bottom-8 right-8 w-14 h-14 bg-primary text-on-primary rounded-full shadow-lg flex items-center justify-center cursor-pointer active:scale-95 transition-transform z-50"
	>
		<span class="material-symbols-outlined" style="font-variation-settings: 'wght' 600"
			>add</span
		>
	</button>
</template>

<script setup>
import ResourceTimeline from "@/components/dashboard/ResourceTimeline.vue";
import OperationalSummaryCards from "@/components/dashboard/OperationalSummaryCards.vue";
import { useDashboard } from "@/composables/dashboard/useDashboard";
import { useProviderTimeline } from "@/composables/dashboard/useProviderTimeline";

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
</script>

<style></style>
