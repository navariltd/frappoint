<template>
	<div class="flex items-center justify-center min-h-screen bg-gray-200 p-6">
		<Alert
			v-if="alertOptions.message"
			:title="alertOptions.title"
			:description="alertOptions.message"
			:variant="alertOptions.variant"
			:theme="alertOptions.theme"
			class="fixed top-8 left-1/2 -translate-x-1/2 z-50 min-w-[300px]"
			@close="alertOptions.message = ''"
		/>
		<div class="bg-white rounded-3xl shadow-xl w-full max-w-5xl overflow-hidden flex flex-col">
			<div class="text-center py-6">
				<h2 class="text-2xl font-bold text-gray-800">Select Date & Time</h2>
			</div>

			<div class="flex flex-1 border-t border-gray-100">
				<div v-if="serviceResource.loading" class="p-6 text-gray-400">
					Loading service details…
				</div>

				<div v-else-if="serviceResource.error" class="p-6 text-red-500">
					Failed to load service
				</div>

				<div v-else class="w-1/3 p-6 border-r border-gray-50 flex flex-col">
					<h1 class="text-2xl font-black uppercase mb-2">
						{{ service.appointment_type }}
					</h1>

					<p class="text-gray-500 text-sm leading-relaxed">
						{{ service.description }}
					</p>

					<div class="mt-auto pt-6">
						<span class="text-xs font-bold uppercase text-gray-400 block mb-1"
							>Duration</span
						>
						<span class="text-sm font-semibold text-gray-700">
							{{ service.default_duration_in_minutes }} mins
						</span>
					</div>
				</div>

				<div class="p-6 flex flex-col items-center justify-center bg-white">
					<div class="w-full max-w-sm">
						<Calendar
							class="custom-mini-calendar"
							:config="calendarConfig"
							v-model="selectedDate"
							@cellClick="onCellClick"
						/>
					</div>
				</div>

				<div class="w-1/4 p-6 bg-gray-50 overflow-y-auto" style="max-height: 500px">
					<p class="text-sm font-semibold text-gray-500 mb-4">
						{{ formattedSelectedDate }}
					</p>

					<div v-if="selectedDate" class="space-y-3">
						<button
							v-for="slot in timeSlots"
							:key="slot"
							@click="selectedTime = slot"
							:class="[
								'w-full py-3 border-2 rounded-lg font-medium transition-all',
								selectedTime === slot
									? 'border-blue-600 bg-blue-50 text-blue-700'
									: 'border-gray-200 text-gray-600 hover:border-blue-300',
							]"
						>
							{{ slot }}
						</button>
					</div>
					<div v-else class="text-center text-gray-400 mt-20 italic">
						Select a date to see availability
					</div>
				</div>
			</div>

			<div class="p-6 flex justify-center border-t border-gray-100">
				<button
					@click="submitBooking"
					:disabled="!selectedDate || !selectedTime"
					class="bg-red-500 hover:bg-red-600 disabled:bg-gray-300 text-white px-16 py-3 rounded-full font-bold text-lg uppercase tracking-widest transition-colors shadow-lg"
				>
					Book
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from "vue";
import { createResource } from "frappe-ui";
import { Calendar, Alert } from "frappe-ui";
import { useRoute } from "vue-router";

const route = useRoute();

const serviceId = computed(() => route.query.service);

const alertOptions = ref({
	title: "",
	message: "",
	variant: "solid",
	theme: "green",
	container: null,
	dialog: null,
});

const serviceResource = createResource({
	url: "frappoint.frappoint.api.service_type.get_service_types",
	params: () => ({
		service: serviceId.value,
	}),
	auto: true,
});

const service = computed(() => {
	return (
		serviceResource.data?.find((s) => s.name === serviceId.value) ||
		serviceResource.data?.[0] ||
		{}
	);
});

const calendarConfig = {
	defaultMode: "Month",
	disableModes: ["Day", "Week"],
	hideHeader: false,
	isEditMode: false,
	disablePast: true,
	allowCustomClickEvents: true,
	enableShortcuts: false,
};

const selectedDate = ref(null);
const selectedTime = ref(null);

const timeSlots = ["12:00am", "12:30am", "1:00am", "4:00am", "4:30am", "5:00am", "5:30am"];

const formattedSelectedDate = computed(() => {
	if (!selectedDate.value) return "";
	return new Date(selectedDate.value).toLocaleDateString("en-US", {
		weekday: "long",
		month: "long",
		day: "numeric",
	});
});

const onCellClick = (date) => {
	selectedDate.value = date;
	selectedTime.value = null;
};

const showAlert = (title, message) => {
	alertOptions.value = {
		title,
		message,
		variant: "solid",
		theme: "green",
	};
	setTimeout(() => {
		alertOptions.value = {
			title: "",
			message: "",
		};
	}, 3000);
};

const submitBooking = () => {
	// alert(`Booking confirmed for ${selectedDate.value} at ${selectedTime.value}`);
	showAlert("Booking Confirmed", `Your appointment is set for ${selectedTime.value}`);
};
</script>
