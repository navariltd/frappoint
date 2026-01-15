<template>
	<AppLayout>
		<div class="flex flex-col h-full">
			<div class="mb-6 px-5 pt-5">
				<TabButtons
					:buttons="[
						{
							label: 'Calendar View',
							value: 'calendar',
						},
						{
							label: 'Portal view',
							value: 'portal',
						},
					]"
					v-model="currentView"
				/>
			</div>

			<div class="flex-1 overflow-auto">
				<CalendarComponent v-if="currentView === 'calendar'" />

				<!-- Provider Portal View -->
				<div
					v-else-if="currentView === 'portal'"
					class="w-full h-full overflow-auto bg-gradient-to-br from-blue-50 to-indigo-50"
				>
					<div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
						<!-- Header with Profile -->
						<div class="flex items-center justify-between mb-8">
							<div>
								<h1 class="text-4xl font-bold text-gray-900 mb-2">
									Welcome back, {{ providerName }}
								</h1>
								<p class="text-gray-600">
									Here's your appointment overview for today
								</p>
							</div>
							<div class="flex-shrink-0">
								<div
									class="w-20 h-20 bg-gradient-to-br from-blue-400 to-indigo-600 rounded-full flex items-center justify-center shadow-lg"
								>
									<span class="text-2xl font-bold text-white">
										{{ providerName.charAt(0).toUpperCase() }}
									</span>
								</div>
							</div>
						</div>

						<!-- Stats Cards with Enhanced Design -->
						<div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
							<div
								class="bg-white rounded-lg p-6 border border-gray-200 shadow-md hover:shadow-lg transition-shadow"
							>
								<div class="flex items-center justify-between">
									<div>
										<p class="text-sm text-gray-500 font-medium mb-2">
											Today's Appointments
										</p>
										<p class="text-3xl font-bold text-gray-900">
											{{ todayCount }}
										</p>
									</div>
									<div
										class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center"
									>
										<CalendarDays class="w-6 h-6 text-blue-600" />
									</div>
								</div>
							</div>
							<div
								class="bg-white rounded-lg p-6 border border-gray-200 shadow-md hover:shadow-lg transition-shadow"
							>
								<div class="flex items-center justify-between">
									<div>
										<p class="text-sm text-gray-500 font-medium mb-2">
											This Week
										</p>
										<p class="text-3xl font-bold text-gray-900">
											{{ weekCount }}
										</p>
									</div>
									<div
										class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center"
									>
										<Clock3 class="w-6 h-6 text-purple-600" />
									</div>
								</div>
							</div>
							<div
								class="bg-white rounded-lg p-6 border border-gray-200 shadow-md hover:shadow-lg transition-shadow"
							>
								<div class="flex items-center justify-between">
									<div>
										<p class="text-sm text-gray-500 font-medium mb-2">
											Upcoming
										</p>
										<p class="text-3xl font-bold text-gray-900">
											{{ upcomingCount }}
										</p>
									</div>
									<div
										class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center"
									>
										<CalendarCheck class="w-6 h-6 text-green-600" />
									</div>
								</div>
							</div>
							<div
								class="bg-white rounded-lg p-6 border border-gray-200 shadow-md hover:shadow-lg transition-shadow"
							>
								<div class="flex items-center justify-between">
									<div>
										<p class="text-sm text-gray-500 font-medium mb-2">
											Completed
										</p>
										<p class="text-3xl font-bold text-blue-600">
											{{ completedCount }}
										</p>
									</div>
									<div
										class="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center"
									>
										<CheckCircle class="w-6 h-6 text-indigo-600" />
									</div>
								</div>
							</div>
						</div>

						<!-- Main Content Grid -->
						<div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
							<!-- Upcoming Appointments -->
							<div class="lg:col-span-2">
								<div
									class="bg-white rounded-lg border border-gray-200 shadow-md overflow-hidden"
								>
									<div
										class="px-6 py-5 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50"
									>
										<h2 class="text-lg font-semibold text-gray-900">
											Upcoming Appointments
										</h2>
									</div>

									<div
										v-if="appointmentsLoading"
										class="flex justify-center items-center py-12"
									>
										<div
											class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"
										></div>
									</div>

									<div
										v-else-if="
											!upcomingAppointments ||
											upcomingAppointments.length === 0
										"
										class="flex flex-col items-center justify-center py-12 px-6 text-center"
									>
										<CalendarX class="w-12 h-12 text-gray-300 mb-3" />
										<p class="text-gray-500">No upcoming appointments</p>
									</div>

									<div v-else class="divide-y divide-gray-100">
										<div
											v-for="appointment in upcomingAppointments"
											:key="appointment.name"
											class="px-6 py-4 hover:bg-blue-50 transition-colors duration-150"
										>
											<div class="flex items-start justify-between gap-4">
												<div class="flex-1">
													<p class="font-semibold text-gray-900">
														{{ appointment.customer }}
													</p>
													<p class="text-sm text-gray-600 mt-1">
														{{ appointment.appointment_type }}
													</p>

													<div class="mt-3 space-y-2">
														<div
															class="flex items-center gap-4 text-sm text-gray-600"
														>
															<div class="flex items-center gap-1">
																<CalendarDays
																	class="w-4 h-4 text-gray-400"
																/>
																<span>{{
																	formatDate(
																		appointment.appointment_date,
																	)
																}}</span>
															</div>
															<div class="flex items-center gap-1">
																<Clock3
																	class="w-4 h-4 text-gray-400"
																/>
																<span
																	>{{ appointment.start_time }} -
																	{{
																		appointment.end_time
																	}}</span
																>
															</div>
														</div>
														<div
															class="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded-md font-medium text-sm"
														>
															<Clock3 class="w-4 h-4" />
															<span
																>{{
																	appointment.duration
																}}
																min</span
															>
														</div>
													</div>
												</div>
												<Badge
													:variant="'subtle'"
													:theme="
														statusToColor[appointment.status] || 'gray'
													"
													size="md"
													label="Badge"
													class="shrink-0"
												>
													{{ appointment.status }}
												</Badge>
											</div>
										</div>
									</div>
								</div>
							</div>

							<!-- Quick Actions & Info Sidebar -->
							<div class="space-y-6">
								<!-- Profile Info Card -->
								<div
									class="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg shadow-md p-6 text-white"
								>
									<h3 class="font-semibold mb-4 text-lg">Profile</h3>
									<div class="space-y-4">
										<div>
											<p class="text-blue-100 text-sm mb-1">Your Role</p>
											<p class="font-semibold text-white">{{ roleLabel }}</p>
										</div>
										<div>
											<p class="text-blue-100 text-sm mb-1">
												Total Customers
											</p>
											<p class="font-semibold text-white">
												{{ totalCustomers }}
											</p>
										</div>
										<div>
											<p class="text-blue-100 text-sm mb-1">
												Today's Schedule
											</p>
											<p class="font-semibold text-white">
												{{ todayCount }}
												{{
													todayCount === 1
														? "appointment"
														: "appointments"
												}}
											</p>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { createListResource } from "frappe-ui";
import { Badge } from "frappe-ui";
import { CalendarDays, Clock3, CalendarX, CalendarCheck, CheckCircle } from "lucide-vue-next";
import CalendarComponent from "@/components/Calendar.vue";
import AppLayout from "@/components/AppLayout.vue";
import TabButtons from "@/components/TabButtons.vue";
import { useUserStore } from "@/data/user";

const currentView = ref("calendar");
const { userDocResource } = useUserStore();
const providerName = computed(() => userDocResource.data?.full_name || "");
const appointmentsLoading = ref(true);

const statusToColor = {
	Open: "gray",
	Confirmed: "blue",
	Completed: "green",
	Rescheduled: "orange",
	Closed: "red",
	"No Show": "red",
	Cancelled: "red",
};

// Determine if current user is an admin/system role
const isAdmin = computed(() => {
	const roles = userDocResource.data?.roles || [];
	return (
		roles.includes("System Manager") ||
		roles.includes("Administrator") ||
		userDocResource.data?.name === "Administrator"
	);
});

// Role label for quick info
const roleLabel = computed(() => (isAdmin.value ? "Administrator" : "Service Provider"));

// Fetch appointments for this provider
const appointmentDocs = createListResource({
	doctype: "Service Appointment",
	fields: [
		"name",
		"status",
		"appointment_date",
		"appointment_provider",
		"appointment_type",
		"start_time",
		"end_time",
		"duration",
		"customer",
	],
	filters: [],
	orderBy: "appointment_date asc",
	start: 0,
	length: 100,
	auto: false,
});

onMounted(async () => {
	// Set filters based on user role
	if (!isAdmin.value && providerName.value) {
		appointmentDocs.filters = [["appointment_provider", "=", providerName.value]];
	}

	// Always reload to fetch appointments
	await appointmentDocs.reload();
	appointmentsLoading.value = false;
});

// Watch for loading state changes
watch(
	() => appointmentDocs.loading,
	(newVal) => {
		appointmentsLoading.value = newVal;
	},
);

// Calculate dates for filtering
const today = new Date();
today.setHours(0, 0, 0, 0);

// Calculate end of current week (Sunday)
const weekEnd = new Date(today);
const daysUntilSunday = (7 - today.getDay()) % 7 || 7;
weekEnd.setDate(today.getDate() + daysUntilSunday);
weekEnd.setHours(23, 59, 59, 999);

// Computed properties for different appointment categories
const upcomingAppointments = computed(() => {
	if (!appointmentDocs.data) return [];
	return appointmentDocs.data.filter((apt) => {
		const aptDate = new Date(apt.appointment_date);
		aptDate.setHours(0, 0, 0, 0);
		return aptDate >= today && ["Open", "Confirmed"].includes(apt.status);
	});
});

const todayCount = computed(() => {
	if (!appointmentDocs.data) return 0;
	return appointmentDocs.data.filter((apt) => {
		const aptDate = new Date(apt.appointment_date);
		aptDate.setHours(0, 0, 0, 0);
		return aptDate.getTime() === today.getTime() && ["Open", "Confirmed"].includes(apt.status);
	}).length;
});

const weekCount = computed(() => {
	if (!appointmentDocs.data) return 0;
	return appointmentDocs.data.filter((apt) => {
		const aptDate = new Date(apt.appointment_date);
		aptDate.setHours(0, 0, 0, 0);
		return (
			aptDate >= today && aptDate <= weekEnd && ["Open", "Confirmed"].includes(apt.status)
		);
	}).length;
});

const upcomingCount = computed(() => {
	if (!appointmentDocs.data) return 0;
	return appointmentDocs.data.filter((apt) => {
		const aptDate = new Date(apt.appointment_date);
		aptDate.setHours(0, 0, 0, 0);
		return aptDate >= today && ["Open", "Confirmed"].includes(apt.status);
	}).length;
});

const completedCount = computed(() => {
	if (!appointmentDocs.data) return 0;
	return appointmentDocs.data.filter((apt) => apt.status === "Completed").length;
});

const totalCustomers = computed(() => {
	if (!appointmentDocs.data) return 0;
	const unique = new Set(appointmentDocs.data.map((apt) => apt.customer));
	return unique.size;
});

// Helper function to format date
const formatDate = (dateStr) => {
	const date = new Date(dateStr);
	return date.toLocaleDateString("en-US", {
		weekday: "short",
		month: "short",
		day: "numeric",
	});
};
</script>
