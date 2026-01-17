<template>
	<div class="flex justify-between p-4 max-w-7xl mx-auto">
		<div class="grow">
			<h2>Upcoming Schedule</h2>
			<p>Manage your appointments and history</p>
		</div>

		<div class="flex flex-end justify-end items-start grow gap-8">
			<div class="flex gap-4">
				<button>List</button>
				<button>Calendar</button>
			</div>
			<div>
				<button>+ New Booking</button>
			</div>
		</div>
	</div>

	<div class="grid grid-cols-1 xl:grid-cols-3 gap-8 max-w-7xl mx-auto">
		<div class="xl:col-span-2 flex flex-col gap-8">
			<div class="flex justify-between px-6">
				<p>NEXT UP</p>
				<p>Confirmed</p>
			</div>

			<AppointmentCard v-if="nextUp" :appointment="nextUp" variant="next" />

			<div>
				Upcoming

				<AppointmentCard
					v-for="appointment in upcomingAppointments"
					:appointment="appointment"
					:key="appointment.id"
				/>
			</div>
		</div>

		<div class="hidden xl:flex flex-col gap-6">
			<div>
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
			<div>Need help?</div>
		</div>
	</div>
</template>

<script setup>
import AppointmentCard from "@/components/AppointmentCard.vue";
import { Calendar } from "frappe-ui";
import { createListResource } from "frappe-ui";
import { computed, onMounted } from "vue";

const appointmentsResourceList = createListResource({
	doctype: "Service Appointment",
	fields: ["*"],
	filters: {},
	orderBy: "appointment_date asc, start_time asc",
});

onMounted(() => {
	appointmentsResourceList.reload();
});

const appointments = computed(() => {
	return appointmentsResourceList.data || [];
});

const nextUp = computed(() => {
	return appointments.value[0] || null;
});

const upcomingAppointments = computed(() => {
	return appointments.value.slice(1);
});
</script>
