<template>
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
			<div>
				<h2 class="text-3xl font-bold text-gray-900">Welcome, {{ username }}</h2>
				<div class="flex gap-6 mt-4">
					<button
						:class="[
							'text-sm font-medium pb-2 border-b-2 transition-all duration-200',
							'hover:text-blue-600',
							activeTab === 'upcoming'
								? 'text-blue-600 border-blue-600'
								: 'text-gray-600 border-transparent',
						]"
						@click="activeTab = 'upcoming'"
					>
						Upcoming
					</button>
					<button
						:class="[
							'text-sm font-medium pb-2 border-b-2 transition-all duration-200',
							'hover:text-blue-600',
							activeTab === 'current'
								? 'text-blue-600 border-blue-600'
								: 'text-gray-600 border-transparent',
						]"
						@click="activeTab = 'current'"
					>
						Current
					</button>
					<button
						:class="[
							'text-sm font-medium pb-2 border-b-2 transition-all duration-200',
							'hover:text-blue-600',
							activeTab === 'previous'
								? 'text-blue-600 border-blue-600'
								: 'text-gray-600 border-transparent',
						]"
						@click="activeTab = 'previous'"
					>
						Previous
					</button>
				</div>
			</div>
			<div class="flex-shrink-0">
				<button
					@click="goToServices"
					class="p-2 rounded bg-blue-500 text-white hover:bg-gray-800 shadow-sm hover:shadow-md transition-all duration-200"
				>
					Book New Appointments
				</button>
			</div>
		</div>

		<div class="border-t border-gray-200 pt-6">
			<!-- Loading state -->
			<div v-if="appointmentDocs.loading">
				<ul class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
					<li v-for="i in 8" :key="i">
						<AppointmentCardSkeleton />
					</li>
				</ul>
			</div>

			<!-- Empty state -->
			<div
				v-else-if="!appointmentDocs.data || appointmentDocs.data.length === 0"
				class="flex flex-col items-center justify-center py-12 text-center"
			>
				<CalendarX class="w-16 h-16 text-gray-300 mb-4" />
				<h3 class="text-lg font-semibold text-gray-900 mb-2">
					No {{ activeTab }} appointments
				</h3>
				<p class="text-gray-500 mb-6">
					{{ getEmptyStateMessage() }}
				</p>
				<button
					v-if="activeTab === 'upcoming' || activeTab === 'current'"
					@click="goToServices"
					class="p-2 rounded bg-blue-500 text-white hover:bg-gray-800 shadow-sm hover:shadow-md transition-all duration-200"
				>
					Book New Appointments
				</button>
			</div>

			<!-- Appointments grid -->
			<ul v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
				<li v-for="appointment in appointmentDocs.data" :key="appointment.name">
					<AppointmentCard
						:name="appointment.name"
						:status="appointment.status"
						:appointment_date="appointment.appointment_date"
						:appointment_provider="appointment.appointment_provider"
						:appointment_type="appointment.appointment_type"
						:start_time="appointment.start_time"
						:end_time="appointment.end_time"
						:duration="appointment.duration"
					/>
				</li>
			</ul>
		</div>
	</div>
</template>

<script setup>
import { createListResource } from "frappe-ui";
import { CalendarX } from "lucide-vue-next";
import { string } from "postcss-selector-parser";
import { computed, ref, watch } from "vue";
import AppointmentCard from "./AppointmentCard.vue";
import AppointmentCardSkeleton from "./AppointmentCardSkeleton.vue";
import { useRouter } from "vue-router";

const router = useRouter();

const goToServices = () => {
	router.push({ name: "Services" });
};

const props = defineProps({
	username: string,
});

const activeTab = ref("upcoming");

const appointmentFilters = computed(() => {
	const today = new Date().toISOString().split("T")[0];

	if (activeTab.value === "current") {
		return [["appointment_date", "=", today]];
	}
	if (activeTab.value === "upcoming") {
		return [["appointment_date", ">", today]];
	}
	return [["appointment_date", "<", today]];
});

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
	],
	filters: appointmentFilters,
	orderBy: "appointment_date desc",
	start: 0,
	length: 5,
	auto: true,
});

watch(activeTab, () => {
	appointmentDocs.reload();
});

function getEmptyStateMessage() {
	if (activeTab.value === "upcoming") {
		return "You don't have any upcoming appointments scheduled.";
	}
	if (activeTab.value === "current") {
		return "You don't have any appointments scheduled for today.";
	}
	return "You don't have any past appointments.";
}
</script>
