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
				<Button
					class="bg-dark-gray-900 hover:bg-gray-800 text-white hover:text-dark-gray-900 shadow-sm hover:shadow-md transition-all duration-200"
				>
					+ Book New Appointments
				</Button>
			</div>
		</div>

		<div class="border-t border-gray-200 pt-6">
			<ul class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
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
import { computed, ref, watch } from "vue";
import { string } from "postcss-selector-parser";
import { createListResource } from "frappe-ui";
import AppointmentCard from "./AppointmentCard.vue";

const props = defineProps({
	username: string,
});

const activeTab = ref("upcoming"); // upcoming, current or previous

const appointmentFilters = computed(() => {
	const today = new Date().toISOString().split("T")[0];

	if (activeTab.value === "current") {
		return [["appointment_date", "=", today]];
	} else if (activeTab.value === "upcoming") {
		return [["appointment_date", ">", today]];
	} else {
		return [["appointment_date", "<", today]];
	}
});

let appointmentDocs = createListResource({
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
</script>
