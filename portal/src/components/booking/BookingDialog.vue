<template>
	<div class="max-w-6xl mx-auto px-4 sm:px-6 py-4 sm:py-6">
		<!-- Backdrop for better contrast -->
		<div
			v-if="alertOptions.message"
			class="fixed inset-0 bg-black/20 backdrop-blur-sm z-[100] transition-opacity duration-300"
			@click="alertOptions.message = ''"
		></div>

		<!-- Alert with enhanced visibility -->
		<Alert
			v-if="alertOptions.message"
			:title="alertOptions.title"
			:description="alertOptions.message"
			:variant="alertOptions.variant"
			:theme="alertOptions.theme"
			class="fixed top-4 md:top-8 left-1/2 -translate-x-1/2 z-[101] w-[90%] md:w-auto md:min-w-[400px] md:max-w-[500px] shadow-2xl animate-slide-down"
			@close="alertOptions.message = ''"
		/>

		<!-- Show errors at the top -->
		<ErrorMessage
			v-if="getAvailableDates.error"
			:message="getAvailableDates.error"
			class="mb-4"
		/>
		<ErrorMessage
			v-if="getAvailableTimeSlots.error"
			:message="getAvailableTimeSlots.error"
			class="mb-4"
		/>
		<ErrorMessage
			v-if="checkSlotAvailability.error"
			:message="checkSlotAvailability.error"
			class="mb-4"
		/>

		<div class="flex flex-col gap-4 sm:gap-6">
			<div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
				<!-- header section  -->
				<div class="flex-1">
					<h1
						class="font-semibold text-xl sm:text-2xl md:text-3xl text-gray-900 leading-tight"
					>
						{{ stepTitle }}
					</h1>
					<p class="text-sm sm:text-base md:text-lg text-gray-600 mt-1">
						{{ stepSubtitle }}
					</p>
				</div>

				<!-- progress section  -->
				<div class="flex gap-3 sm:gap-4 md:gap-6 text-xs sm:text-sm md:text-base">
					<div class="flex items-center gap-1.5">
						<span
							:class="[
								currentStep >= 1
									? 'bg-primary text-white'
									: 'bg-gray-200 text-gray-500',
								'w-6 h-6 sm:w-7 sm:h-7 rounded-full flex items-center justify-center font-semibold text-xs sm:text-sm',
							]"
							>1</span
						>
						<span
							:class="
								currentStep >= 1 ? 'font-semibold text-gray-900' : 'text-gray-500'
							"
							class="hidden sm:inline"
							>Select Time</span
						>
					</div>
					<div class="flex items-center gap-1.5">
						<span
							:class="[
								currentStep >= 2
									? 'bg-primary text-white'
									: 'bg-gray-200 text-gray-500',
								'w-6 h-6 sm:w-7 sm:h-7 rounded-full flex items-center justify-center font-semibold text-xs sm:text-sm',
							]"
							>2</span
						>
						<span
							:class="
								currentStep >= 2 ? 'font-semibold text-gray-900' : 'text-gray-500'
							"
							class="hidden sm:inline"
							>Details</span
						>
					</div>
					<div class="flex items-center gap-1.5">
						<span
							:class="[
								currentStep >= 3
									? 'bg-primary text-white'
									: 'bg-gray-200 text-gray-500',
								'w-6 h-6 sm:w-7 sm:h-7 rounded-full flex items-center justify-center font-semibold text-xs sm:text-sm',
							]"
							>3</span
						>
						<span
							:class="
								currentStep >= 3 ? 'font-semibold text-gray-900' : 'text-gray-500'
							"
							class="hidden sm:inline"
							>Payment</span
						>
					</div>
				</div>
			</div>

			<!-- Main Booking Card Step Content  -->
			<div
				class="bg-white rounded-xl sm:rounded-2xl shadow-lg overflow-hidden flex flex-col min-h-[500px] sm:min-h-[600px]"
			>
				<!-- Step Components -->
				<div class="flex-1 flex flex-col lg:flex-row">
					<!-- Show skeleton while initially loading dates -->
					<SlotPickerSkeleton
						v-if="
							currentStep === 1 &&
							getAvailableDates.loading &&
							availableDates.length === 0
						"
					/>

					<!-- Show SlotPicker once dates are available or loaded -->
					<SlotPicker
						v-else-if="currentStep === 1"
						:date="booking.draft.date"
						:slot="booking.draft.slot"
						:provider="booking.draft.provider"
						:available-dates="availableDates"
						:available-slots="availableSlots"
						:can-proceed="canProceed"
						:dates-loading="getAvailableDates.loading"
						:slots-loading="getAvailableTimeSlots.loading"
						@update:date="booking.setDate"
						@update:slot="booking.setSlot"
						@update:provider="booking.setProvider"
						@continue="currentStep++"
					/>

					<UserDetails v-if="currentStep === 2" :is-logged-in="isLoggedIn" />

					<PaymentStep
						v-if="currentStep === 3"
						:can-proceed="canProceed"
						@back="currentStep--"
						@submit="submitBooking"
					/>
				</div>

				<div
					v-if="appointmentBasket.length"
					class="border-t border-gray-100 bg-gray-50/70 px-6 md:px-8 py-5"
				>
					<div class="flex flex-col gap-4">
						<div class="flex items-center justify-between gap-4">
							<div>
								<h3 class="text-sm font-semibold text-gray-900">Booking Basket</h3>
								<p class="text-xs text-gray-500">
									{{ appointmentBasket.length }} appointment{{
										appointmentBasket.length === 1 ? "" : "s"
									}}
									added
								</p>
							</div>
							<div class="text-right">
								<p class="text-xs text-gray-500">Estimated total</p>
								<p class="text-lg font-bold text-primary">
									{{ formatCurrency(basketTotal, booking.draft.currency) }}
								</p>
							</div>
						</div>

						<div class="space-y-3 max-h-56 overflow-auto pr-1">
							<div
								v-for="(appointment, index) in appointmentBasket"
								:key="`${appointment.appointment_type}-${index}`"
								class="rounded-xl border border-gray-200 bg-white p-4 flex items-start justify-between gap-4"
							>
								<div class="space-y-1">
									<p class="font-semibold text-gray-900">
										{{ appointment.appointment_type }}
									</p>
									<p class="text-sm text-gray-600">
										{{ appointment.guest_full_name }}
									</p>
									<p class="text-xs text-gray-500">
										{{ appointment.date }} •
										{{ formatSlotLabel(appointment.slot) }}
									</p>
								</div>
								<div class="text-right space-y-2">
									<p class="text-sm font-semibold text-gray-900">
										{{
											formatCurrency(
												appointment.price,
												appointment.currency || booking.draft.currency
											)
										}}
									</p>
									<button
										type="button"
										class="text-xs text-red-600 hover:underline"
										@click="booking.removeAppointmentFromBasket(index)"
									>
										Remove
									</button>
								</div>
							</div>
						</div>

						<div class="flex items-center justify-between gap-3">
							<button
								type="button"
								class="text-sm text-gray-500 hover:text-gray-800"
								@click="booking.clearAppointmentBasket()"
							>
								Clear basket
							</button>
							<p class="text-xs text-gray-500">
								You can keep adding services before payment.
							</p>
						</div>
					</div>
				</div>

				<!-- Buttons for step 1 (Choose Time) -->
				<div
					v-if="currentStep === 1"
					class="mt-auto px-6 md:px-8 pb-6 md:pb-8 flex items-center justify-between border-t border-gray-100 pt-6"
				>
					<button
						@click="closeDialog"
						class="px-6 py-3 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-semibold hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
						type="button"
					>
						Back
					</button>
					<button
						:disabled="!canProceed"
						@click="currentStep++"
						class="px-8 py-3 rounded-lg bg-primary hover:bg-primary-dark text-white font-semibold shadow-lg shadow-primary/30 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
						type="button"
					>
						Continue to Details
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 5l7 7-7 7"
							/>
						</svg>
					</button>
				</div>

				<!-- Buttons for step 2 (integrated in form) -->
				<div
					v-if="currentStep === 2"
					class="mt-auto px-6 md:px-8 pb-6 md:pb-8 flex items-center justify-between border-t border-gray-100 pt-6"
				>
					<button
						@click="currentStep--"
						class="px-6 py-3 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-semibold hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
						type="button"
					>
						Back
					</button>
					<button
						:disabled="!canProceed"
						@click="
							() => {
								booking.addAppointmentToBasket({ resetCurrent: true });
								showAlert('Added', 'Appointment added to booking basket', 'green');
								currentStep = 1;
							}
						"
						class="px-8 py-3 rounded-lg border border-gray-300 text-gray-700 font-semibold hover:bg-gray-50 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
						type="button"
					>
						Add to Booking
					</button>
					<button
						:disabled="!canProceed"
						@click="
							() => {
								booking.addAppointmentToBasket({ resetCurrent: true });
								currentStep = 3;
							}
						"
						class="px-8 py-3 rounded-lg bg-primary hover:bg-primary-dark text-white font-semibold shadow-lg shadow-primary/30 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
						type="button"
					>
						Pay Now
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { createResource, ErrorMessage, Alert } from "frappe-ui";
import { ref, watch, computed, onMounted } from "vue";
import { useAlert } from "@/composables/useAlert";
import { useBookingStore } from "@/stores/bookingStore";
import { useAuthStore } from "@/stores/auth";
import { useRouter, useRoute } from "vue-router";
import SlotPicker from "./steps/ChooseTime.vue";
import SlotPickerSkeleton from "./SlotPickerSkeleton.vue";
import UserDetails from "./steps/CustomerDetails.vue";
import PaymentStep from "./steps/PaymentAndConfirmation.vue";
import { flattenSlotsByProviderForDate } from "@/utils/slotTransformation";
import { formatCurrency } from "@/utils";

const booking = useBookingStore();
const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const { alertOptions, showAlert } = useAlert();

const serviceType = computed(() => booking.draft.serviceType);

function closeDialog() {
	router.back();
}

const availableDates = ref([]);
const availableSlots = ref([]);
const isLoggedIn = ref(false);

const currentStep = computed({
	get: () => booking.currentStep,
	set: (v) => (booking.currentStep = v),
});

const stepTitle = computed(() => {
	if (currentStep.value === 1) return "Select a Date & Time";
	if (currentStep.value === 2) return "Your Details";
	return "Payment";
});

const stepSubtitle = computed(() => {
	if (currentStep.value === 1) return `Choose the best time for your ${serviceType.value}`;
	if (currentStep.value === 2) return "Enter your details or confirm your information";
	return "Confirm your booking and proceed to payment";
});

const canProceed = computed(() => {
	if (currentStep.value === 1) return booking.draft.date && booking.draft.slot;
	if (currentStep.value === 2) {
		// Check primary guest info
		const hasBasicInfo =
			booking.draft.email && booking.draft.mobileNo && booking.draft.fullName;

		// Check all guests have required full_name
		const allGuestsValid =
			booking.draft.guests &&
			Array.isArray(booking.draft.guests) &&
			booking.draft.guests.length > 0 &&
			booking.draft.guests.every((guest) => guest.full_name && guest.full_name.trim());

		return hasBasicInfo && allGuestsValid;
	}
	return appointmentBasket.value.length > 0;
});

const appointmentBasket = computed(() => booking.draft.appointments || []);

const basketTotal = computed(() =>
	appointmentBasket.value.reduce((total, item) => total + (Number(item.price) || 0), 0)
);

const getAvailableDates = createResource({
	url: "frappoint.frappoint.api.slot_availability.get_available_dates",
	method: "GET",
	makeParams() {
		return {
			service_type: serviceType.value,
			duration: booking.draft.duration,
		};
	},
});

const getAvailableTimeSlots = createResource({
	url: "frappoint.frappoint.api.slot_availability.get_available_time_slots",
	method: "GET",
	makeParams() {
		return {
			service_type: serviceType.value,
			duration: booking.draft.duration,
			date: booking.draft.date,
		};
	},
});

const checkSlotAvailability = createResource({
	url: "frappoint.frappoint.api.slot_availability.check_slot_availability",
	method: "GET",
	makeParams() {
		return {
			slot_ids: booking.draft.slot.slot_ids,
		};
	},
});

const paymentLinkResource = createResource({
	url: "frappoint.payments.get_payment_link",
	auto: false,
});

const bookingDeskResource = createResource({
	url: "frappoint.frappoint.api.booking_desk.create_booking",
	auto: false,
});

function formatSlotLabel(slot) {
	if (!slot?.start_time || !slot?.end_time) return "Time not set";
	return `${slot.start_time} - ${slot.end_time}`;
}

onMounted(async () => {
	booking.loadFromStorage();

	if (!booking.draft.serviceType) {
		router.replace({ name: "Services" });
		return;
	}

	await booking.hydrateServiceDetails();

	if (booking.draft.date) {
		await loadSlotsForDate(booking.draft.date);
	}
	availableDates.value = await getAvailableDates.fetch();
});

watch(
	() => booking.draft.date,
	(date) => {
		if (booking.isResettings) return;
		if (!date || !booking.draft.serviceType) return;

		loadSlotsForDate(date);
	}
);

async function loadSlotsForDate(date) {
	if (!date || !booking.draft.serviceType) return;

	const response = await getAvailableTimeSlots.fetch();
	availableSlots.value = flattenSlotsByProviderForDate(response, date);
}

const customerResource = createResource({
	url: "frappoint.frappoint.api.user.get_logged_in_customer",
	method: "GET",
	auto: false,
});

watch(
	() => currentStep.value,
	async (step) => {
		if (step === 2 && auth.isLoggedIn) {
			try {
				const res = await customerResource.fetch();
				if (res) {
					booking.draft.customer = res.customer || "";
					booking.draft.fullName = res.contact.contact_display || "";
					booking.draft.email = res.contact.contact_email || "";
					booking.draft.mobileNo = res.contact.contact_phone || "";
				}
			} catch (err) {
				console.error("Failed to fetch customer info", err);
			}
		}
	},
	{ immediate: true }
);

// TODO: Check validate customer appointment for same date and time

async function submitBooking() {
	const appointmentItems =
		booking.draft.appointments && booking.draft.appointments.length
			? [...booking.draft.appointments]
			: booking.isComplete
			? [booking.createAppointmentSnapshot()]
			: [];

	if (!appointmentItems.length) return;

	if (!auth.isLoggedIn) {
		booking.currentStep = currentStep.value;
		booking.saveToStorage();

		router.push({
			name: "Login",
			query: {
				redirect: route.fullPath,
			},
		});
		return;
	}

	try {
		const payload = {
			customer: {
				customer: booking.draft.customer,
				fullName: booking.draft.fullName,
				email: booking.draft.email,
				mobileNo: booking.draft.mobileNo,
			},
			guests: appointmentItems,
		};

		const resp = await bookingDeskResource.submit(payload);

		if (!resp || !resp.booking_id) {
			return;
		}

		const bookingTotal = Number(resp.grand_total || 0);
		if (bookingTotal > 0) {
			const redirectTo = `${window.location.origin}/portal/booking/${resp.booking_id}`;
			const response = await paymentLinkResource.submit({
				reference_doctype: "Service Booking",
				reference_docname: resp.booking_id,
				payment_gateway: booking.draft.selectedPaymentGateway,
				redirect_to: redirectTo,
			});

			if (typeof response === "string" && response) {
				booking.clearStorage();
				window.location.href = response;
				return;
			}
		} else {
			booking.clearStorage();
			router.push({
				name: "BookingConfirmation",
				params: { bookingId: resp.booking_id },
			});
		}
	} catch (error) {
		console.error("Failed to submit booking:", error);
		showAlert("Error", getErrorMessage(error), "red");
	}
}

function getErrorMessage(error) {
	if (error?.messages?.length) {
		return error.messages[0];
	}

	if (error?.message) {
		return error.message;
	}

	if (error?._server_messages) {
		try {
			const messages = JSON.parse(error._server_messages);
			if (messages.length > 0) {
				const parsed = JSON.parse(messages[0]);
				return parsed.message || "Failed to submit booking. Please try again.";
			}
		} catch (parseError) {
			console.error("Failed to parse server error message:", parseError);
		}
	}

	return "Failed to submit booking. Please try again.";
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
