<template>
	<div class="min-h-screen bg-gray-50 p-3 sm:p-6">
		<!-- Header Section -->
		<div
			class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4 sm:gap-0 mb-6 sm:mb-8 max-w-7xl mx-auto"
		>
			<div>
				<h1 class="text-2xl sm:text-3xl font-bold text-gray-900 mb-1">
					Upcoming Schedule
				</h1>
				<p class="text-sm sm:text-base text-gray-500">
					Manage your appointments and history
				</p>
			</div>

			<div class="flex items-center gap-2 sm:gap-4 w-full sm:w-auto">
				<!-- View Toggle -->
				<div
					class="flex bg-white rounded-lg shadow-sm border border-gray-200 p-0.5 sm:p-1"
				>
					<button
						@click="viewMode = 'list'"
						:class="[
							'flex items-center gap-1 sm:gap-2 px-2 sm:px-4 py-1.5 sm:py-2 rounded-md text-xs sm:text-sm font-medium transition-colors',
							viewMode === 'list'
								? 'bg-teal-600 text-white'
								: 'text-gray-600 hover:text-gray-900',
						]"
					>
						<svg
							class="w-3.5 h-3.5 sm:w-4 sm:h-4"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 6h16M4 12h16M4 18h16"
							/>
						</svg>
						<span class="hidden xs:inline">List</span>
					</button>
					<button
						@click="viewMode = 'calendar'"
						:class="[
							'flex items-center gap-1 sm:gap-2 px-2 sm:px-4 py-1.5 sm:py-2 rounded-md text-xs sm:text-sm font-medium transition-colors',
							viewMode === 'calendar'
								? 'bg-teal-600 text-white'
								: 'text-gray-600 hover:text-gray-900',
						]"
					>
						<svg
							class="w-3.5 h-3.5 sm:w-4 sm:h-4"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
							/>
						</svg>
						<span class="hidden xs:inline">Calendar</span>
					</button>
				</div>

				<!-- New Booking Button -->
				<button
					@click="goToServices"
					class="flex items-center justify-center gap-1.5 sm:gap-2 bg-gray-900 text-white px-3 sm:px-6 py-2 sm:py-2.5 rounded-lg hover:bg-gray-800 transition-colors shadow-sm font-medium text-xs sm:text-sm whitespace-nowrap flex-1 sm:flex-none"
				>
					<svg
						class="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 4v16m8-8H4"
						/>
					</svg>
					<span class="hidden xs:inline">New Booking</span>
					<span class="xs:hidden">New</span>
				</button>
			</div>
		</div>

		<!-- Main Content -->
		<div class="max-w-7xl mx-auto">
			<!-- Calendar View -->
			<div v-if="viewMode === 'calendar'" class="bg-white rounded-2xl shadow-sm p-4 sm:p-6">
				<Calendar
					:config="calendarConfig"
					:events="calendarEvents"
					@update="(event) => console.log(`Updateing event with id ${event.id}`)"
					@cancel="(event) => console.log(`canceling event with id ${event.id}`)"
				/>
			</div>

			<!-- List View -->
			<div v-else class="grid grid-cols-1 xl:grid-cols-3 gap-4 sm:gap-6">
				<!-- Left Column - Appointments List -->
				<div class="xl:col-span-2 space-y-4 sm:space-y-6">
					<!-- Loading State -->
					<div v-if="appointmentsResourceList.loading" class="space-y-4">
						<AppointmentCardSkeleton v-for="i in 3" :key="i" />
					</div>

					<!-- Empty State -->
					<div
						v-else-if="
							!nextUp &&
							upcomingAppointments.length === 0 &&
							pastAppointments.length === 0
						"
						class="bg-white rounded-2xl shadow-sm p-8 sm:p-12 text-center"
					>
						<div class="max-w-md mx-auto">
							<div
								class="w-16 h-16 sm:w-20 sm:h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4"
							>
								<svg
									class="w-8 h-8 sm:w-10 sm:h-10 text-gray-400"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
									/>
								</svg>
							</div>
							<h3 class="text-lg sm:text-xl font-bold text-gray-900 mb-2">
								You have no bookings yet
							</h3>
							<p class="text-sm sm:text-base text-gray-500 mb-6">
								Start by browsing our services and booking your first appointment.
							</p>
							<button
								@click="router.push({ name: 'Services' })"
								class="inline-flex items-center justify-center gap-2 bg-gray-900 text-white px-6 py-3 rounded-lg hover:bg-gray-800 transition-colors shadow-sm font-medium text-sm"
							>
								<svg
									class="w-5 h-5"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M12 4v16m8-8H4"
									/>
								</svg>
								Browse Services
							</button>
						</div>
					</div>

					<!-- Next Up Section -->
					<div v-if="nextUp">
						<div class="flex justify-between items-center mb-3 sm:mb-4">
							<h3
								class="text-xs sm:text-sm font-semibold text-gray-400 tracking-wider"
							>
								NEXT UP
							</h3>
							<span
								class="px-2 sm:px-3 py-0.5 sm:py-1 bg-green-50 text-green-600 text-[10px] sm:text-xs font-medium rounded-full"
								>Confirmed</span
							>
						</div>
						<AppointmentCard :appointment="nextUp" variant="next" />
					</div>

					<!-- Upcoming Section -->
					<div v-if="upcomingAppointments.length > 0">
						<h3
							class="text-xs sm:text-sm font-semibold text-gray-400 tracking-wider mb-3 sm:mb-4"
						>
							UPCOMING
						</h3>
						<div class="space-y-3 sm:space-y-4">
							<AppointmentCard
								v-for="appointment in upcomingAppointments"
								:appointment="appointment"
								:key="appointment.name"
							/>
						</div>
					</div>

					<!-- Past Section -->
					<div v-if="pastAppointments.length > 0">
						<h3
							class="text-xs sm:text-sm font-semibold text-gray-400 tracking-wider mb-3 sm:mb-4"
						>
							PAST
						</h3>
						<div class="space-y-3 sm:space-y-4">
							<AppointmentCard
								v-for="appointment in pastAppointments"
								:appointment="appointment"
								:key="appointment.name"
								variant="past"
							/>
						</div>
					</div>
				</div>

				<!-- Right Column - Calendar & Rewards -->
				<div class="hidden xl:flex flex-col gap-6">
					<!-- Calendar Widget -->
					<div class="bg-white rounded-2xl shadow-sm p-6">
						<Calendar
							:config="{
								defaultMode: 'Month',
								isEditMode: false,
								eventIcons: {},
								allowCustomClickEvents: true,
								enableShortcuts: false,
							}"
						/>
					</div>

					<!-- Rewards Card -->
					<div
						class="bg-gradient-to-br from-teal-600 to-teal-700 rounded-2xl shadow-lg p-6 text-white"
					>
						<div class="flex items-center gap-2 mb-3">
							<svg
								class="w-6 h-6"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
								/>
							</svg>
						</div>
						<p class="text-xs font-medium opacity-90 mb-2">REWARDS</p>
						<h3 class="text-xl font-semibold mb-4">
							You have 2 free sessions pending
						</h3>
						<button
							class="w-full bg-white text-teal-600 font-medium py-3 rounded-lg hover:bg-gray-50 transition-colors"
						>
							Redeem Now
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Calendar, createListResource } from "frappe-ui";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { handleAppointmentCancel, handleAppointmentReschedule } from "@/utils";
import AppointmentCard from "@/components/booking/AppointmentCard.vue";
import AppointmentCardSkeleton from "@/components/booking/AppointmentCardSkeleton.vue";

const router = useRouter();
const viewMode = ref("list");

const calendarConfig = {
	defaultMode: "Month",
	isEditMode: false,
	eventIcons: {},
	allowCustomClickEvents: true,
	enableShortcuts: false,
};

const appointmentsResourceList = createListResource({
	doctype: "Service Appointment",
	fields: ["*"],
	filters: {
		status: ["not in", ["Cancelled", "Rescheduled", "No Show"]],
	},
	orderBy: "appointment_date asc, start_time asc",
});

onMounted(() => {
	appointmentsResourceList.reload();
});

const appointments = computed(() => {
	return appointmentsResourceList.data || [];
});

// Helper function to check if an appointment is in the past
const isAppointmentPast = (appointment) => {
	const appointmentDate = new Date(appointment.appointment_date);
	const today = new Date();
	today.setHours(0, 0, 0, 0);
	appointmentDate.setHours(0, 0, 0, 0);
	return appointmentDate < today;
};

// Helper function to check if an appointment is today or in the future
const isAppointmentUpcoming = (appointment) => {
	const appointmentDate = new Date(appointment.appointment_date);
	const today = new Date();
	today.setHours(0, 0, 0, 0);
	appointmentDate.setHours(0, 0, 0, 0);
	return appointmentDate >= today;
};

// Filter upcoming appointments (today and future)
const upcomingAppointmentsAll = computed(() => {
	return appointments.value.filter((apt) => isAppointmentUpcoming(apt));
});

const nextUp = computed(() => {
	return upcomingAppointmentsAll.value[0] || null;
});

const upcomingAppointments = computed(() => {
	return upcomingAppointmentsAll.value.slice(1);
});

// Filter past appointments
const pastAppointments = computed(() => {
	return appointments.value
		.filter((apt) => isAppointmentPast(apt))
		.sort((a, b) => {
			// Sort by date descending (most recent first)
			const dateA = new Date(a.appointment_date);
			const dateB = new Date(b.appointment_date);
			return dateB - dateA;
		});
});

const statusColorMap = {
	Confirmed: "green",
	Open: "amber",
	Completed: "gray",
	Closed: "violet",
};

// Transform appointments for Calendar component
const calendarEvents = computed(() => {
	return appointments.value.map((apt) => {
		// Determine color based on status
		const color = statusColorMap[apt.status] || "blue";

		return {
			id: apt.name,
			title: apt.appointment_type || "Appointment",
			participant: apt.appointment_provider || "Provider unknown",
			fromDate: apt.appointment_date,
			toDate: apt.appointment_date,
			fromTime: apt.start_time,
			toTime: apt.end_time,
			venue: apt.service_unit || apt.company,
			color: color,
			isFullDay: false,
		};
	});
});

function goToServices() {
	router.push({ name: "Services" });
}
</script>
