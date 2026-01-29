<template>
	<div class="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8 flex flex-col items-center">
		<div class="max-w-lg w-full bg-white rounded-2xl shadow-xl overflow-hidden mt-8">
			<!-- Service Image Banner -->
			<div class="h-40 w-full relative bg-gray-200">
				<img
					v-if="serviceTypeImage"
					:src="serviceTypeImage"
					class="absolute inset-0 w-full h-full object-cover"
					alt="Service"
				/>
				<div
					v-else
					class="absolute inset-0 w-full h-full flex items-center justify-center text-gray-400 bg-gradient-to-br from-teal-200 to-blue-200"
				>
					<FeatherIcon name="image" class="w-12 h-12" />
				</div>
			</div>
			<!-- Color Gradient Banner -->

			<div class="p-6 sm:p-8">
				<div class="text-xs font-bold text-primary uppercase tracking-wider mb-2">
					Step 1 of 1
				</div>
				<h1 class="text-2xl font-bold text-gray-900 mb-2">Cancel your appointment?</h1>
				<p class="text-gray-500 mb-4">
					We're sorry to see you go. If you need to reschedule instead, you can do that
					from the dashboard. Otherwise, please provide a reason for cancellation.
				</p>

				<!-- Appointment Summary -->
				<div class="flex items-center gap-4 bg-gray-50 rounded-lg p-4 mb-4">
					<img
						v-if="serviceTypeImage"
						:src="serviceTypeImage"
						class="w-12 h-12 rounded object-cover border-2 border-white shadow-sm"
						alt="Service"
					/>
					<div class="flex-1">
						<div class="font-semibold text-gray-900">
							{{ appointment.doc.appointment_type }}
						</div>
						<div class="text-xs text-gray-500">
							{{ formatDate(appointment.doc.appointment_date) }} at
							{{ formatTime(appointment.doc.start_time) }}
						</div>
					</div>
				</div>

				<!-- Reason Dropdown -->
				<div class="mb-4">
					<label class="block text-sm font-medium text-gray-700 mb-1"
						>Reason for Cancellation</label
					>
					<select
						v-model="reason"
						class="w-full border rounded-lg px-3 py-2 text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary"
					>
						<option value="" disabled>Select a reason...</option>
						<option v-for="option in reasons" :key="option" :value="option">
							{{ option }}
						</option>
					</select>
				</div>

				<!-- Cancellation Policy -->
				<div
					class="bg-orange-50 border border-orange-200 text-orange-800 rounded-lg p-3 text-sm flex items-start gap-2 mb-4"
				>
					<FeatherIcon name="alert-triangle" class="w-5 h-5 mt-0.5 text-orange-400" />
					<span>
						Cancellations made within 24 hours of the appointment time may incur a 50%
						service fee. This fee will be charged to your card on file.
					</span>
				</div>

				<!-- Action Buttons -->
				<div class="flex flex-col gap-2 mt-6">
					<button
						:disabled="!reason || cancelling"
						@click="handleCancel"
						class="w-full bg-teal-600 text-white font-semibold py-3 rounded-xl hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
					>
						<span
							v-if="cancelling"
							class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"
						></span>
						Yes, Cancel Appointment
					</button>
					<button
						@click="router.back()"
						class="w-full text-gray-500 font-medium py-3 rounded-xl hover:bg-gray-100 transition-colors"
					>
						Nevermind, keep appointment
					</button>
				</div>
			</div>
			<div class="text-center text-xs text-gray-400 py-4">
				Having trouble?
				<a href="#" class="text-primary font-medium hover:underline">Contact Support</a>
			</div>
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon, createDocumentResource, createResource } from "frappe-ui";
import { useRoute, useRouter } from "vue-router";
import { ref, computed, watch } from "vue";

const route = useRoute();
const router = useRouter();
const appointmentId = route.params.id;
const reason = ref("");
const reasons = [
	"Schedule conflict",
	"Feeling better",
	"Found another provider",
	"Cost concerns",
	"Other",
];
const cancelling = ref(false);

const appointment = createDocumentResource({
	doctype: "Service Appointment",
	name: appointmentId,
	auto: true,
	onSuccess(doc) {
		if (doc.appointment_type) serviceTypeResource.fetch();
	},
});

const serviceTypeResource = createResource({
	url: "frappe.client.get",
	makeParams() {
		return {
			doctype: "Service Type",
			name: appointment.doc?.appointment_type,
		};
	},
});

const serviceTypeImage = computed(() => serviceTypeResource.data?.image);

function formatDate(dateStr) {
	if (!dateStr) return "";
	const date = new Date(dateStr);
	return date.toLocaleDateString("en-US", {
		weekday: "short",
		month: "short",
		day: "numeric",
		year: "numeric",
	});
}

function formatTime(timeStr) {
	if (!timeStr) return "";
	const [hours, minutes] = timeStr.split(":");
	const hour = parseInt(hours);
	const ampm = hour >= 12 ? "AM" : "PM";
	const displayHour = hour % 12 || 12;
	return `${displayHour}:${minutes} ${ampm}`;
}

const cancelResource = createResource({
	url: "frappoint.frappoint.doctype.service_appointment.service_appointment.cancel_appointment",
});

async function handleCancel() {
	if (!reason.value) return;
	cancelling.value = true;
	try {
		await cancelResource.submit({
			appointment_id: appointmentId,
		});
		router.push({ name: "Bookings" });
	} catch (error) {
		alert("Failed to cancel appointment. Please try again.");
	} finally {
		cancelling.value = false;
	}
}
</script>

<style scoped>
.bg-gradient {
	background: linear-gradient(135deg, #4fd1c5 0%, #4299e1 100%);
}
</style>
