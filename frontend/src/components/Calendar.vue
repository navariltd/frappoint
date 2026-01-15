<template>
	<div class="flex-1 flex flex-col h-full w-full overflow-hidden">
		<Calendar
			v-if="!appointments.loading"
			:config="calendarConfig"
			:events="appointments.data"
			@click="onEventClick"
			@dblClick="onEventDblClick"
			@cellClick="onCellClick"
			class="flex-1 w-full h-full"
			
		/>
		<div v-else class="flex-1 flex items-center justify-center">Loading calendar...</div>
	</div>
</template>

<script setup>
import { createResource, Calendar } from "frappe-ui";

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

// Event Handlers
const onEventClick = (event) => console.log("Clicked event:", event);
const onEventDblClick = (event) => console.log("Double clicked:", event);
const onCellClick = (data) => console.log("Clicked empty cell:", data);
</script>
