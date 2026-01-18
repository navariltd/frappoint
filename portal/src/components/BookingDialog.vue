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
							<h1 class="font-semibold text-3xl">Select a Date & Time</h1>
							<p class="text-lg text-gray-700">
								Choose the best time for your {{ serviceType }}
							</p>
						</div>

						<!-- progress section  -->

						<div class="flex gap-6">
							<span>1 Select Time</span>
							<span>2 Details</span>
							<span>3 Payment</span>
						</div>
					</div>

					<!-- Main Booking Card  -->

					<div
						class="flex flex-col lg:flex-row min-h-[600px] justify-between items-start bg-surface-light rounded-2xl shadow-soft overflow-hidden"
					>
						<!-- LEFT COLUMN: Calendar  -->
						<div
							class="w-full lg:w-5/12 p-6 md:p-8 border-b lg:border-b-0 lg:border-r border-slate-100 bg-white flex flex-col"
						>
							<DatePicker
								v-model="selectedDate"
								:allowed-dates="availableDates"
								variant="subtle"
								:disabled="false"
							/>
						</div>

						<!-- RIGHT COLUMN: Time Slots  -->
						<div
							v-if="selectedDate"
							class="w-full lg:w-7/12 p-6 md:p-8 flex flex-col bg-surface-light relative"
						>
							<!-- provider  -->
							<div class="mb-8 border-collapse">
								<FormControl
									type="select"
									:options="providerOptions"
									v-model="selectedProvider"
									size="xl"
									variant="subtle"
									placeholder="Any Available Staff"
									:disabled="false"
									label="Select Staff Member (Optional)"
									class="w-full appearance-none bg-white text-slate-900 px-4 pr-10 focus:!outline-none focus:!ring-2 focus:!ring-primary/50 focus:!border-primary transition-shadow cursor-pointer"
								/>
							</div>

							<!-- Date and slots  -->
							<div>
								<div class="flex items-center justify-between mb-4">
									<h1 class="text-lg font-bold text-slate-900">
										{{ formatSelectedDate(selectedDate) }}
									</h1>
								</div>

								<div
									class="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-8 overflow-y-auto max-h-[320px] time-slot-scroll pr-2"
								>
									<div class="col-span-full mt-2 mb-1">
										<p>Morning</p>
									</div>

									<Button
										v-for="slot in morningSlots"
										:key="slot.start_time + slot.provider"
										@click="selectSlot(slot)"
										:class="
											selectedSlot === slot
												? '!bg-primary !text-white'
												: 'border hover-bg-primary/10'
										"
										class="py-4 px-4 rounded-lg border border-slate-200 text-slate-700 hover:border-primary hover:text-primary hover:bg-[#E2F0F9] transition-all text-sm font-medium"
										>{{ formatTime(slot.start_time) }}</Button
									>

									<div class="col-span-full mt-2 mb-1">
										<p>Afternoon</p>
									</div>

									<Button
										v-for="slot in afternoonSlots"
										:key="slot.start_time + slot.provider"
										@click="selectSlot(slot)"
										:class="
											selectedSlot === slot
												? '!bg-primary !text-white'
												: 'broder hover-bg-primary/10'
										"
										class="py-4 px-4 rounded-lg border border-slate-200 text-slate-700 hover:border-primary hover:text-primary hover:bg-[#E2F0F9] transition-all text-sm font-medium"
										>{{ formatTime(slot.start_time) }}</Button
									>
								</div>
							</div>

							<!-- Footer Action Area  -->
							<div class="mt-auto pt-6 border-t border-slate-100">
								<div
									class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
								>
									<!-- Summary  -->
									<div class="flex items-start gap-3">
										<div
											class="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-slate-500"
										>
											<FeatherIcon class="h-4" name="clock" />
										</div>
										<div>
											<p class="text-sm font-bold text-slate-900">
												{{ serviceType }}
											</p>
											<p v-if="selectedSlot" class="text-xs text-slate-500">
												{{ servicePrice }} .
												{{ formatTime(selectedSlot.start_time) }}
											</p>
										</div>
									</div>

									<!-- Buttons  -->
									<div class="flex items-center gap-3 w-full sm:w-auto">
										<Button
											@click="$emit('close')"
											class="flex-1 sm:flex-none py-2.5 px-6 rounded-lg border border-slate-300 text-slate-700 font-semibold text-sm hover:bg-slate-50 transition-colors"
											>Back</Button
										>
										<Button
											:disabled="!selectedDate || !selectedSlot"
											@click="submitBooking"
											class="flex-1 sm:flex-none py-2.5 px-6 rounded-lg !bg-primary hover:!bg-primary-dark text-white font-semibold text-sm shadow-lg shadow-primary/30 transition-all flex items-center justify-center gap-2"
											>Continue</Button
										>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import {
	Button,
	createListResource,
	createResource,
	DatePicker,
	Dialog,
	FeatherIcon,
	FormControl,
} from "frappe-ui";
import { ref, watch, computed, onMounted } from "vue";
import { useBookingStore } from "@/stores/bookingStore";
import { formatCurrency } from "@/utils";

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

const providerOptions = computed(() => {
	const map = new Map();

	for (const slot of availableSlots.value) {
		if (!map.has(slot.provider)) {
			map.set(slot.provider, {
				label: slot.provider_name,
				value: slot.provider,
			});
		}
	}

	return [{ label: "Any Available Staff", value: null }, ...Array.from(map.values())];
});

const visibleSlots = computed(() => {
	if (!selectedProvider.value) {
		return availableSlots.value;
	}

	return availableSlots.value.filter((slot) => slot.provider === selectedProvider.value);
});

const morningSlots = computed(() =>
	visibleSlots.value.filter((s) => Number(s.start_time.split(":")[0]) < 12)
);

const afternoonSlots = computed(() =>
	visibleSlots.value.filter((s) => Number(s.start_time.split(":")[0]) >= 12)
);

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

	$emit("close");
}

function formatTime(time) {
	if (!time) return "";

	const [h, m] = time.split(":");
	const date = new Date();
	date.setHours(h, m);
	return date.toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
	});
}

function formatSelectedDate(date) {
	if (!date) return "";

	const jsDate = new Date(`${date}T00:00:00`);

	if (isNaN(jsDate.getTime())) return "";

	return jsDate.toLocaleDateString("en-US", {
		weekday: "long",
		month: "long",
		day: "numeric",
	});
}
</script>
