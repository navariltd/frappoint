<template>
	<div
		v-if="isVisible"
		class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
		@click.self="close"
	>
		<div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 overflow-hidden">
			<!-- Header -->
			<div class="bg-blue-600 text-white p-4 flex justify-between items-center">
				<h3 class="text-lg font-semibold">Appointment Details</h3>
				<button @click="close" class="text-white hover:text-gray-200 transition-colors">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-6 w-6"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>

			<!-- Loading State -->
			<div v-if="loading" class="p-8 text-center">
				<div
					class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"
				></div>
				<p class="mt-4 text-gray-600">Loading appointment details...</p>
			</div>

			<!-- Content -->
			<div v-else-if="appointment" class="p-6 space-y-4">
				<!-- Debug Info (remove after testing) -->
				<div class="text-xs text-gray-400 mb-2 p-2 bg-gray-50 rounded">
					Debug: {{ Object.keys(appointment).length }} fields loaded
				</div>
				<!-- Customer Info -->
				<div class="flex items-start space-x-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-5 w-5 text-gray-400 mt-0.5"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
						/>
					</svg>
					<div>
						<p class="text-sm text-gray-500">Customer</p>
						<p class="font-medium">
							{{ appointment.full_name || appointment.customer }}
						</p>
					</div>
				</div>

				<!-- Service Type -->
				<div class="flex items-start space-x-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-5 w-5 text-gray-400 mt-0.5"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
						/>
					</svg>
					<div>
						<p class="text-sm text-gray-500">Service Type</p>
						<p class="font-medium">{{ appointment.appointment_type }}</p>
					</div>
				</div>

				<!-- Provider -->
				<div class="flex items-start space-x-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-5 w-5 text-gray-400 mt-0.5"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
					<div>
						<p class="text-sm text-gray-500">Service Provider</p>
						<p class="font-medium">{{ appointment.appointment_provider }}</p>
					</div>
				</div>

				<!-- Date & Time -->
				<div class="flex items-start space-x-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-5 w-5 text-gray-400 mt-0.5"
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
					<div>
						<p class="text-sm text-gray-500">Date & Time</p>
						<p class="font-medium">{{ formatDate(appointment.appointment_date) }}</p>
						<p class="text-sm text-gray-600">
							{{ appointment.start_time }} - {{ appointment.end_time }}
							<span class="text-gray-500">({{ appointment.duration }} min)</span>
						</p>
					</div>
				</div>

				<!-- Status -->
				<div class="flex items-start space-x-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-5 w-5 text-gray-400 mt-0.5"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
					<div>
						<p class="text-sm text-gray-500">Status</p>
						<span
							class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
							:class="getStatusColor(appointment.status)"
						>
							{{ appointment.status }}
						</span>
					</div>
				</div>

				<!-- Details/Notes -->
				<div v-if="appointment.details" class="flex items-start space-x-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-5 w-5 text-gray-400 mt-0.5"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
						/>
					</svg>
					<div>
						<p class="text-sm text-gray-500">Details</p>
						<p class="text-sm text-gray-700">{{ appointment.details }}</p>
					</div>
				</div>
			</div>

			<!-- Error State -->
			<div v-else-if="error" class="p-6 text-center">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="h-12 w-12 text-red-500 mx-auto"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<p class="mt-4 text-gray-600">Failed to load appointment details</p>
				<button
					@click="close"
					class="mt-4 px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors"
				>
					Close
				</button>
			</div>

			<!-- Empty/Unknown State -->
			<div v-else class="p-6 text-center">
				<p class="text-gray-600">No appointment data available</p>
				<p class="text-xs text-gray-400 mt-2">
					Loading: {{ loading }}, Error: {{ error }}, Appointment: {{ !!appointment }}
				</p>
				<button
					@click="close"
					class="mt-4 px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors"
				>
					Close
				</button>
			</div>

			<!-- Footer Actions -->
			<div
				v-if="appointment && !error"
				class="bg-gray-50 px-6 py-4 flex justify-end space-x-3"
			>
				<button
					@click="close"
					class="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors"
				>
					Close
				</button>
				<button
					@click="viewDetails"
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
				>
					View Full Details
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import { createResource } from "frappe-ui";

const props = defineProps({
	isVisible: Boolean,
	appointmentId: String,
});

const emit = defineEmits(["close", "viewDetails"]);

const loading = ref(false);
const error = ref(false);
const appointment = ref(null);

const appointmentResource = createResource({
	url: "frappe.client.get",
	auto: false,
	onSuccess(data) {
		console.log("Appointment data fetched:", data);
		appointment.value = data;
		loading.value = false;
		error.value = false;
	},
	onError(err) {
		console.error("Failed to fetch appointment:", err);
		loading.value = false;
		error.value = true;
	},
});

// // Watch for changes in visibility and appointmentId together
// watch(
// 	() => [props.isVisible, props.appointmentId],
// 	([visible, id]) => {
// 		console.log("EventCard watch triggered:", { visible, id });
// 		if (visible && id) {
// 			fetchAppointment(id);
// 		} else if (!visible) {
// 			// Reset state when modal closes
// 			appointment.value = null;
// 			error.value = false;
// 			loading.value = false;
// 		}
// 	},
// 	{ immediate: true },
// );

function fetchAppointment(id) {
	console.log("Fetching appointment:", id);
	loading.value = true;
	error.value = false;
	appointment.value = null;

	appointmentResource.fetch({
		doctype: "Service Appointment",
		name: id,
	});
}

function close() {
	emit("close");
}

function viewDetails() {
	emit("viewDetails", appointment.value);
}

function formatDate(dateStr) {
	if (!dateStr) return "";
	const date = new Date(dateStr);
	return date.toLocaleDateString("en-US", {
		weekday: "long",
		year: "numeric",
		month: "long",
		day: "numeric",
	});
}

function getStatusColor(status) {
	const colors = {
		Open: "bg-blue-100 text-blue-800",
		Confirmed: "bg-green-100 text-green-800",
		Completed: "bg-gray-100 text-gray-800",
		Cancelled: "bg-red-100 text-red-800",
		Rescheduled: "bg-yellow-100 text-yellow-800",
		"No Show": "bg-orange-100 text-orange-800",
		Closed: "bg-gray-100 text-gray-800",
	};
	return colors[status] || "bg-gray-100 text-gray-800";
}
</script>
