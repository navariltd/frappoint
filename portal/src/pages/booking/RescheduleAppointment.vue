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
						</div>

						<div
							class="hidden md:block w-72 h-48 rounded-xl bg-gray-100 overflow-hidden relative"
						>
							<div
								class="w-full h-full"
								:style="
									serviceTypeImage
										? {
												backgroundImage: `url(${serviceTypeImage})`,
												backgroundSize: 'cover',
												backgroundPosition: 'center',
										  }
										: {
												background:
													'linear-gradient(to bottom right, #3a8a8b, #2c7677, #1f5a5b)',
										  }
								"
							></div>
						</div>
					</div>
				</div>

				<!-- New Selection Section -->
				<div>
					<h3 class="text-xl font-bold text-gray-900 mb-4">Select New Date & Time</h3>
					<div
						class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden"
					>
						<!-- Show skeleton while initially loading dates -->
						<SlotPickerSkeleton
							v-if="getAvailableDates.loading && availableDates.length === 0"
						/>

						<!-- Show SlotPicker once dates are available or loaded -->
						<SlotPicker
							v-else
							:date="reschedulingState.date"
							:slot="reschedulingState.slot"
							:provider="reschedulingState.provider"
							:available-dates="availableDates"
							:available-slots="availableSlots"
							:dates-loading="getAvailableDates.loading"
							:slots-loading="getAvailableTimeSlots.loading"
							@update:date="handleDateChange"
							@update:slot="(val) => (reschedulingState.slot = val)"
							@update:provider="(val) => (reschedulingState.provider = val)"
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

			<!-- Backdrop for better contrast -->
			<div
				v-if="alert.show"
				class="fixed inset-0 bg-black/20 backdrop-blur-sm z-[100] transition-opacity duration-300"
				@click="alert.show = false"
			></div>

			<!-- Alert with enhanced visibility -->
			<Alert
				v-if="alert.show"
				:title="alert.title"
				:description="alert.message"
				:variant="alert.variant"
				:theme="alert.theme"
				class="fixed top-4 md:top-8 left-1/2 -translate-x-1/2 z-[101] w-[90%] md:w-auto md:min-w-[400px] md:max-w-[500px] shadow-2xl animate-slide-down"
				@close="alert.show = false"
			/>
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon, createDocumentResource, createResource, Alert } from "frappe-ui";
import { useRoute, useRouter } from "vue-router";
import { computed, watch, ref, nextTick } from "vue";
import SlotPicker from "@/components/booking/steps/ChooseTime.vue";
import SlotPickerSkeleton from "@/components/booking/SlotPickerSkeleton.vue";

const route = useRoute();
const router = useRouter();

const appointmentId = route.params.id;
const rescheduling = ref(false);
const alert = ref({
	show: false,
	title: "",
	message: "",
	variant: "solid",
	theme: "green",
});

// --- Available Dates/Slots logic (from BookingDialog.vue) ---
const availableDates = ref([]);
const availableSlots = ref([]);

const reschedulingState = ref({
	date: null,
	slot: null,
	provider: null,
	serviceType: null,
	duration: null,
});

const appointment = createDocumentResource({
	doctype: "Service Appointment",
	name: appointmentId,
	auto: true,
});

const getAvailableDates = createResource({
	url: "frappoint.frappoint.api.slot_availability.get_available_dates",
	method: "GET",
	makeParams() {
		return {
			service_type: reschedulingState.value.serviceType,
			duration: reschedulingState.value.duration,
		};
	},
	auto: false,
	async onSuccess(data) {
		availableDates.value = data || [];
		await nextTick();
	},
});

watch(
	() => appointment.doc,
	async (doc) => {
		if (doc?.appointment_type) {
			reschedulingState.value.serviceType = doc.appointment_type;
			reschedulingState.value.duration = doc.duration;
			await getAvailableDates.fetch();
			await serviceTypeResource.fetch();
		}
	},
	{ immediate: true }
);

const getAvailableTimeSlots = createResource({
	url: "frappoint.frappoint.api.slot_availability.get_available_time_slots",
	method: "GET",
	makeParams() {
		return {
			service_type: reschedulingState.value.serviceType,
			duration: reschedulingState.value.duration,
			date: reschedulingState.value.date,
		};
	},
});

watch(
	() => reschedulingState.value.date,
	(newDate) => {
		if (newDate) loadSlotsForDate(newDate);
	}
);

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

const rescheduleResource = createResource({
	url: "frappoint.frappoint.doctype.service_appointment.service_appointment.reschedule_appointment",
});

async function loadSlotsForDate(date) {
	if (!date || !reschedulingState.value.serviceType) return;

	const response = await getAvailableTimeSlots.fetch();

	// Find the date group matching the requested date
	// Response structure: [{ date: "2026-05-10", slots: [...] }, ...]
	const dateGroup = response.find((group) => group.date === date);

	if (!dateGroup || !dateGroup.slots) {
		availableSlots.value = [];
		return;
	}

	// Flatten providers within each time slot into individual selectable slots
	availableSlots.value = dateGroup.slots.flatMap((slot) =>
		(slot.providers || []).map((provider) => ({
			start_time: slot.start_time,
			end_time: slot.end_time,
			duration: slot.duration,
			buffer_before: slot.buffer_before,
			buffer_after: slot.buffer_after,
			provider: provider.provider,
			provider_name: provider.provider_name,
			service_unit: provider.service_unit,
			service_unit_name: provider.service_unit_name,
			slot_ids: provider.slot_ids,
			shift_assignment: provider.shift_assignment,
		}))
	);
}

const isValidSelection = computed(() => {
	return reschedulingState.value.date && reschedulingState.value.slot;
});

const newSelectionDisplay = computed(() => {
	if (!reschedulingState.value.date || !reschedulingState.value.slot) return null;

	const date = new Date(reschedulingState.value.date);
	const dateStr = date.toLocaleDateString("en-US", {
		weekday: "long",
		month: "short",
		day: "numeric",
	});
	const timeStr = formatTime(reschedulingState.value.slot.start_time);

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

function handleDateChange(newDate) {
	if (!newDate) return;

	let formattedDate = newDate;
	if (newDate instanceof Date) {
		// Correct for timezone offset to prevent the date jumping back by one day
		const offset = newDate.getTimezoneOffset();
		const correctedDate = new Date(newDate.getTime() - offset * 60 * 1000);
		formattedDate = correctedDate.toISOString().split("T")[0];
	}

	reschedulingState.value.date = formattedDate;
	reschedulingState.value.slot = null;
}

async function handleConfirmReschedule() {
	if (!isValidSelection.value) return;

	rescheduling.value = true;
	try {
		// 1. Create new appointment via reschedule_appointment
		const result = await rescheduleResource.submit({
			appointment_name: appointmentId,
			new_appointment_date: reschedulingState.value.date,
			new_start_time: reschedulingState.value.slot.start_time,
			new_end_time: reschedulingState.value.slot.end_time,
			new_provider: reschedulingState.value.slot.provider,
			new_slot_ids: JSON.stringify(reschedulingState.value.slot.slot_ids),
		});

		if (!result?.success) {
			throw new Error("Reschedule failed");
		}

		alert.value = {
			show: true,
			title: "Success!",
			message: "Your appointment has been rescheduled successfully.",
			variant: "solid",
			theme: "green",
		};

		// Delay redirect
		setTimeout(() => {
			router.replace({ name: "AppointmentDetails", params: { id: result.new_appointment } });
		}, 2000);
	} catch (error) {
		console.error(error);
		// Extract error message from various possible error structures
		let errorMessage = "Failed to reschedule. Please try again.";
		if (error.messages && error.messages.length > 0) {
			errorMessage = error.messages[0];
		} else if (error.message) {
			errorMessage = error.message;
		} else if (error._server_messages) {
			try {
				const messages = JSON.parse(error._server_messages);
				if (messages.length > 0) {
					const parsed = JSON.parse(messages[0]);
					errorMessage = parsed.message || errorMessage;
				}
			} catch (e) {
				console.error(e.message);
			}
		}

		alert.value = {
			show: true,
			title: "Error",
			message: errorMessage,
			variant: "solid",
			theme: "red",
		};
	} finally {
		rescheduling.value = false;
	}
}
</script>
<style scoped>
@keyframes slide-down {
	from {
		opacity: 0;
		transform: translate(-50%, -100%);
	}
	to {
		opacity: 1;
		transform: translate(-50%, 0);
	}
}

.animate-slide-down {
	animation: slide-down 0.3s ease-out;
}
</style>
