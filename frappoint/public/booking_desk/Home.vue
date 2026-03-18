<template>
	<div class="h-screen flex flex-col">
		<!-- Top Navigation -->
		<div class="flex gap-2 p-4 border-b">
			<button @click="currentView = 'appointments'">Appointments</button>
			<button @click="currentView = 'calendar'">Calendar</button>
			<button @click="currentView = 'services'">Services</button>
			<button @click="currentView = 'staff'">Staff</button>
		</div>

		<!-- Dynamic View -->
		<div class="flex-1 overflow-auto">
			<div v-if="currentView === 'appointments'">Appointments View</div>
			<div v-if="currentView === 'calendar'">Calendar Views</div>
			<div v-if="currentView === 'services'">Services View</div>
			<div v-if="currentView === 'staff'">Staff View</div>
		</div>
	</div>
</template>

<script setup>
import { ref } from "vue";

const currentView = ref("calendar");
</script>
