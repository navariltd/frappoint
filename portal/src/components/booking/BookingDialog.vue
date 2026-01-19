<template>
	<Dialog
		v-model="props.openBooking"
		:options="{
			size: '6xl',
		}"
	>
		<template #body-title>
			{{ serviceType }}
		</template>
		<template #body-content>
			<div class="max-w-6xl mx-auto px-6 py-6">
				<div class="flex flex-col gap-6">
					<div class="flex justify-between items-center">
						<!-- header section  -->
						<div>
							<h1 class="font-semibold text-3xl">{{ stepTitle }}</h1>
							<p class="text-lg text-gray-700">{{ stepSubtitle }}</p>
						</div>

						<!-- progress section  -->
						<div class="flex gap-6">
							<span :class="currentStep >= 1 ? 'font-bold' : ''">1 Select Time</span>
							<span :class="currentStep >= 2 ? 'font-bold' : ''">2 Details</span>
							<span :class="currentStep >= 3 ? 'font-bold' : ''">3 Payment</span>
						</div>
					</div>

					<!-- Main Booking Card Step Content  -->
					<div
						class="flex flex-col lg:flex-row min-h-[600px] justify-between items-start bg-surface-light rounded-2xl shadow-soft overflow-hidden"
					>
						<!-- Step Components -->
						<SlotPicker
							v-if="currentStep === 1"
							v-model:selected-date="selectedDate"
							v-model:selected-provider="selectedProvider"
							:selected-slot="selectedSlot"
							:available-dates="availableDates"
							:available-slots="availableSlots"
							:service-type="serviceType"
							:service-price="servicePrice"
							@select-slot="selectSlot"
						/>

						<UserDetails
							v-if="currentStep === 2"
							v-model:user-details="userDetails"
							:is-logged-in="isLoggedIn"
						/>

						<PaymentStep
							v-if="currentStep === 3"
							:service-type="serviceType"
							:selected-date="selectedDate"
							:selected-slot="selectedSlot"
							:selected-provider="selectedProvider"
							:user-details="userDetails"
							:service-price="servicePrice"
						/>

						<!-- Buttons  -->
						<div class="flex items-center gap-3 w-full sm:w-auto p-6">
							<Button
								v-if="currentStep > 1"
								@click="currentStep--"
								class="flex-1 sm:flex-none py-2.5 px-6 rounded-lg border border-slate-300 text-slate-700 font-semibold text-sm hover:bg-slate-50 transition-colors"
							>
								Back
							</Button>
							<Button
								v-if="currentStep < 3"
								:disabled="!canProceed"
								@click="currentStep++"
								class="flex-1 sm:flex-none py-2.5 px-6 rounded-lg !bg-primary hover:!bg-primary-dark text-white font-semibold text-sm shadow-lg shadow-primary/30 transition-all flex items-center justify-center gap-2"
							>
								Continue
							</Button>

							<Button
								v-else
								:disabled="!canProceed"
								@click="submitBooking"
								class="flex-1 sm:flex-none py-2.5 px-6 rounded-lg !bg-primary hover:!bg-primary-dark text-white font-semibold text-sm shadow-lg shadow-primary/30 transition-all flex items-center justify-center gap-2"
							>
								Pay
							</Button>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, createListResource, createResource, Dialog } from "frappe-ui";
import { ref, watch, computed, onMounted } from "vue";
import { useBookingStore } from "@/stores/bookingStore";
import { formatCurrency } from "@/utils";
import SlotPicker from "./steps/ChooseTime.vue";
import UserDetails from "./steps/CustomerDetails.vue";
import PaymentStep from "./steps/PaymentAndConfirmation.vue";

const props = defineProps({
	openBooking: Boolean,
});

const emit = defineEmits(["update:openBooking", "close"]);

const booking = useBookingStore();

const serviceType = computed(() => booking.draft.serviceType);
const servicePrice = computed(() => formatCurrency(booking.draft.price, booking.draft.currency));

function closeDialog() {
	emit("update:openBooking", false);
	emit("close");
}

const selectedDate = ref(null);
const selectedSlot = ref(null);
const selectedProvider = ref(null);
const availableDates = ref([]);
const availableSlots = ref([]);
const currentStep = ref(1);

const userDetails = ref({
	name: "",
	email: "",
	phone: "",
});
const isLoggedIn = ref(false);

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
	if (currentStep.value === 1) return selectedDate.value && selectedSlot.value;
	if (currentStep.value === 2) return userDetails.value.name && userDetails.value.email;
	return true;
});

const serviceAppointmentResource = createListResource({
	doctype: "Service Appointment",
});

const getAvailableDates = createResource({
	url: "frappoint.frappoint.api.slot_availability.get_available_dates",
	method: "GET",
	makeParams() {
		return {
			service_type: serviceType.value,
		};
	},
});

const getAvailableTimeSlots = createResource({
	url: "frappoint.frappoint.api.slot_availability.get_available_time_slots",
	method: "GET",
	makeParams() {
		return {
			service_type: serviceType.value,
			date: selectedDate.value,
		};
	},
});

const checkSlotAvailability = createResource({
	url: "frappoint.frappoint.api.slot_availability.check_slot_availability",
	method: "GET",
	makeParams() {
		return {
			slot_ids: selectedSlot.value.slot_ids,
		};
	},
});

onMounted(async () => {
	if (!props.openBooking) return;
	availableDates.value = await getAvailableDates.fetch();
});

watch(selectedDate, async (date) => {
	if (!date) return;

	const response = await getAvailableTimeSlots.fetch();

	availableSlots.value = response.flatMap((provider) =>
		(provider.available_dates || [])
			.filter((d) => d.date === date)
			.flatMap((d) =>
				(d.slots || []).map((slot) => ({
					...slot,
					provider: provider.provider,
					provider_name: provider.provider_name,
					date: d.date,
				}))
			)
	);

	selectedSlot.value = null;
});

function selectSlot(slot) {
	selectedSlot.value = slot;
}

async function submitBooking() {
	if (!selectedDate.value || !selectedSlot.value) return;

	const validation = await checkSlotAvailability.fetch();
	if (!validation.available) {
		alert("Slot no longer available, pick another");
		return;
	}

	// create appointment
	await serviceAppointmentResource.create({
		appointment_type: serviceType.value,
		appointment_date: selectedDate.value,
		start_time: selectedSlot.value.start_time,
		end_time: selectedSlot.value.end_time,
		provider: selectedSlot.value.provider,
	});

	closeDialog();
}
</script>
