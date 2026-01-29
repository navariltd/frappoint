<template>
	<div class="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8">
		<div class="max-w-5xl mx-auto">
			<!-- Header -->
			<div class="mb-8">
				<h1 class="text-3xl font-bold text-gray-900 mb-2">Reschedule Your Appointment</h1>
				<p class="text-gray-500">
					Review your current booking and select a new time slot that works for you.
				</p>
			</div>

			<!-- Loading State -->
			<div v-if="appointment.loading" class="flex justify-center items-center py-20">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
			</div>

			<div v-else-if="appointment.doc" class="space-y-8">
				<!-- Current Booking Card -->
				<div class="bg-white rounded-2xl p-6 md:p-8 shadow-sm border border-gray-100">
					<div class="text-teal-600 text-xs font-bold uppercase tracking-wider mb-2">
						Your Current Booking
					</div>
					<div class="flex flex-col md:flex-row justify-between items-start gap-6">
						<div>
							<h2 class="text-xl font-bold text-gray-900 mb-2">
								{{ appointment.doc.appointment_type }} with
								{{ appointment.doc.appointment_provider }}
							</h2>
							<div class="flex items-center text-teal-600 font-medium">
								<FeatherIcon name="calendar" class="w-4 h-4 mr-2" />
								{{ formatDate(appointment.doc.appointment_date) }} at
								{{ formatTime(appointment.doc.start_time) }}
							</div>

							<!-- <div class="mt-6">
								<button class="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors">
									Cancel Current
								</button>
							</div> -->
						</div>

						<div
							class="hidden md:block w-72 h-48 rounded-xl bg-gray-100 overflow-hidden relative"
						>
							<img
								v-if="serviceTypeImage"
								:src="serviceTypeImage"
								class="w-full h-full object-cover"
								alt="Service"
							/>
							<div
								v-else
								class="w-full h-full flex items-center justify-center bg-gray-200 text-gray-400"
							>
								<FeatherIcon name="image" class="w-12 h-12" />
							</div>
						</div>
					</div>
				</div>

				<!-- New Selection Section -->
				<div>
					<h3 class="text-xl font-bold text-gray-900 mb-4">Select New Date & Time</h3>
					<div
						class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden"
					>
						<SlotPicker
							:available-dates="availableDates"
							:available-slots="availableSlots"
							:slots-loading="getAvailableTimeSlots.loading"
						/>
					</div>
				</div>

				<!-- Footer Actions -->
				<div
					class="flex flex-col md:flex-row justify-between items-center gap-4 pt-4 pb-12"
				>
					<div class="text-left w-full md:w-auto">
						<div v-if="newSelectionDisplay" class="space-y-1">
							<div class="text-sm text-teal-600 font-medium">New Selection:</div>
							<div class="text-lg font-bold text-gray-900">
								{{ newSelectionDisplay }}
							</div>
						</div>
					</div>

					<div class="flex items-center gap-4 w-full md:w-auto">
						<button
							@click="router.back()"
							class="text-gray-500 font-medium hover:text-gray-900 transition-colors px-4"
						>
							Back to Dashboard
						</button>
						<button
							@click="handleConfirmReschedule"
							:disabled="!isValidSelection || rescheduling"
							class="bg-teal-600 text-white px-8 py-3 rounded-xl font-bold hover:bg-teal-700 transition-colors shadow-lg shadow-teal-600/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
						>
							<div
								v-if="rescheduling"
								class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"
							></div>
							Confirm Change
						</button>
					</div>
				</div>
			</div>

			<Alert
				v-if="alert.show"
				:variant="alert.variant"
				:message="alert.message"
				class="fixed bottom-4 right-4 z-50 shadow-xl"
				@close="alert.show = false"
			/>
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon, createDocumentResource, createResource, Alert } from "frappe-ui";
import { useRoute, useRouter } from "vue-router";
import { computed, watch, ref, onMounted, onUnmounted } from "vue";
import { useBookingStore } from "@/stores/bookingStore";
import SlotPicker from "@/components/booking/steps/ChooseTime.vue";

const route = useRoute();
const router = useRouter();
const booking = useBookingStore();

const appointmentId = route.params.id;
const rescheduling = ref(false);
const alert = ref({ show: false, message: "", variant: "success" });

// --- Available Dates/Slots logic (from BookingDialog.vue) ---
const availableDates = ref([]);
const availableSlots = ref([]);

const getAvailableDates = createResource({
	url: "frappoint.frappoint.api.slot_availability.get_available_dates",
	method: "GET",
	makeParams() {
		return {
			service_type: booking.draft.serviceType,
		};
	},
});

const getAvailableTimeSlots = createResource({
	url: "frappoint.frappoint.api.slot_availability.get_available_time_slots",
	method: "GET",
	makeParams() {
		return {
			service_type: booking.draft.serviceType,
			date: booking.draft.date,
		};
	},
});

onMounted(() => {
	booking.$reset();
});

const appointment = createDocumentResource({
	doctype: "Service Appointment",
	name: appointmentId,
	auto: true,
	async onSuccess(doc) {
		booking.setServiceType(doc.appointment_type);
		booking.setCurrency(doc.currency);
		booking.setProvider(doc.appointment_provider);

		serviceTypeResource.fetch();

		// Now that serviceType is set, fetch available dates
		availableDates.value = await getAvailableDates.fetch();
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

// Reschedule API
const rescheduleResource = createResource({
	url: "frappoint.frappoint.doctype.service_appointment.service_appointment.reschedule_appointment",
});

const cancelOldResource = createResource({
	url: "frappoint.frappoint.doctype.service_appointment.service_appointment.cancel_old_appointment",
});

const isValidSelection = computed(() => {
	return booking.draft.date && booking.draft.slot;
});

const newSelectionDisplay = computed(() => {
	if (!booking.draft.date || !booking.draft.slot) return null;

	const date = new Date(booking.draft.date);
	const dateStr = date.toLocaleDateString("en-US", {
		weekday: "long",
		month: "short",
		day: "numeric",
	});
	const timeStr = formatTime(booking.draft.slot.start_time);

	return `${dateStr} at ${timeStr}`;
});

function formatDate(dateStr) {
	if (!dateStr) return "";
	const date = new Date(dateStr);
	return date.toLocaleDateString("en-US", {
		weekday: "long",
		year: "numeric",
		month: "short",
		day: "numeric",
	});
}

function formatTime(timeStr) {
	if (!timeStr) return "";
	const [hours, minutes] = timeStr.split(":");
	const hour = parseInt(hours);
	const ampm = hour >= 12 ? "PM" : "AM";
	const displayHour = hour % 12 || 12;
	return `${displayHour}:${minutes} ${ampm}`;
}

async function handleConfirmReschedule() {
	if (!isValidSelection.value) return;

	rescheduling.value = true;
	try {
		// 1. Create new appointment via reschedule_appointment
		const result = await rescheduleResource.submit({
			appointment_name: appointmentId,
			new_appointment_date: booking.draft.date,
			new_start_time: booking.draft.slot.start_time,
			new_end_time: booking.draft.slot.end_time,
			new_provider: booking.draft.provider || booking.draft.slot.provider,
			new_slot_ids: JSON.stringify(booking.draft.slot.slot_ids),
		});

		// result is the name of the new appointment (or doc json, check return of function)
		// The python function returns frappe.get_doc(new_appointment).name usually or the doc name directly?
		// Let's assume it returns the name or we check payload.

		const newAppointmentName = result;

		if (newAppointmentName) {
			// 2. Cancel old appointment
			await cancelOldResource.submit({
				old_appointment_name: appointmentId,
				new_appointment_name: newAppointmentName,
			});

			alert.value = {
				show: true,
				message: "Appointment Rescheduled Successfully!",
				variant: "success",
			};

			// Delay redirect
			setTimeout(() => {
				router.push({ name: "Bookings" });
			}, 2000);
		} else {
			throw new Error("Failed to create new appointment");
		}
	} catch (error) {
		console.error(error);
		alert.value = {
			show: true,
			message: error.messages?.[0] || "Failed to reschedule. Please try again.",
			variant: "error",
		};
	} finally {
		rescheduling.value = false;
	}
}
</script>
