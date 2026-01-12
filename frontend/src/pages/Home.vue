<template>
	<div class="flex h-screen bg-gray-100 relative">
		<AppLayout>
			<button
				@click="goToAppointments"
				class="absolute bottom-4 right-4 bg-blue-600 text-white px-6 py-3 rounded-lg shadow-lg hover:bg-blue-700 transition flex items-center gap-2 z-50"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="h-5 w-5"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
					/>
				</svg>
				View Appointments
			</button>

			<div class="flex-1 flex flex-col h-full overflow-hidden p-5">
				<CalendarComponent />
			</div>
		</AppLayout>
	</div>
</template>

<script setup>
import { useRouter } from "vue-router";
import CalendarComponent from "@/components/Calendar.vue";
import AppLayout from "@/components/AppLayout.vue";

const router = useRouter();

function goToAppointments() {
	router.push({ name: "Appointments" });
}
</script>
