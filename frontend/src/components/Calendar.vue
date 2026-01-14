<template>
	<div class="flex-1 flex flex-col h-full w-full overflow-hidden">
		<Calendar
			v-if="!appointments.loading"
			:config="calendarConfig"
			:events="appointments.data"
			@click="onEventClick"
			@cellClick="onCellClick"
			class="flex-1 w-full h-full"
		/>
		<div v-else class="flex-1 flex items-center justify-center">Loading calendar...</div>

		<EventCard
			:isVisible="showEventCard"
			:appointmentId="selectedAppointmentId"
			@close="closeEventCard"
			@viewDetails="handleViewDetails"
		/>
	</div>
</template>

<script setup>
import { ref } from "vue";
import { createResource, Calendar } from "frappe-ui";
import EventCard from "./EventCard.vue";

const showEventCard = ref(false);
const selectedAppointmentId = ref(null);

const calendarConfig = {
	defaultMode: "Month",
	isEditMode: false,
	allowCustomClickEvents: true,
	enableShortcuts: true,
	allowSetColor: true,
};

const appointments = createResource({
	url: "frappoint.frappoint.doctype.service_appointment.service_appointment.get_events",
	params: {
		// TODO: Remove this hard coded values
		start: "2026-01-01",
		end: "2026-12-31",
	},
	auto: true,

	transform: (data) => {
		return data.map((e) => ({
			id: e.name,
			title: `${e.customer} • ${e.appointment_provider}`,
			participant: e.appointment_provider,
			venue: e.location || "",
			fromDate: e.start.split(" ")[0],
			toDate: e.end.split(" ")[0],
			fromTime: e.start.split(" ")[1].slice(0, 5),
			toTime: e.end.split(" ")[1].slice(0, 5),
			color: e.color || "#3b82f6",
		}));
	},
});

const onEventClick = (eventData) => {
	const event = eventData?.calendarEvent;

	if (event && event.id) {
		selectedAppointmentId.value = event.id;
		showEventCard.value = true;
	} else {
		console.error("No valid event found:", eventData);
	}
};

const onCellClick = (data) => {
	console.log("Clicked empty cell:", data);
};

const closeEventCard = () => {
	showEventCard.value = false;
	selectedAppointmentId.value = null;
};

const handleViewDetails = (appointment) => {
	console.log("View full details:", appointment);
	// TODO: Navigate to full appointment details page
	// router.push({ name: 'AppointmentDetails', params: { id: appointment.name } })
};
</script>
