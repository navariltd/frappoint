<template>
	<div
		v-if="isVisible"
		class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
		@click.self="close"
	>
		<div
			class="bg-white rounded-lg shadow-xl max-w-2xl w-full overflow-hidden max-h-[90vh] flex flex-col"
		>
			<!-- Header -->
			<div class="bg-blue-600 text-white p-4 flex justify-between items-center">
				<div>
					<h3 class="text-lg font-semibold">Book Appointment</h3>
					<p class="text-sm text-blue-100">{{ service?.appointment_type }}</p>
				</div>
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

			<!-- Progress Steps -->
			<div class="bg-gray-50 px-6 py-4">
				<div class="flex items-center justify-between">
					<div
						v-for="(stepItem, index) in steps"
						:key="index"
						class="flex items-center"
						:class="{ 'flex-1': index < steps.length - 1 }"
					>
						<div class="flex items-center">
							<div
								class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors"
								:class="
									step > index
										? 'bg-green-500 text-white'
										: step === index
										? 'bg-blue-600 text-white'
										: 'bg-gray-300 text-gray-600'
								"
							>
								<span v-if="step > index">✓</span>
								<span v-else>{{ index + 1 }}</span>
							</div>
							<span
								class="ml-2 text-sm font-medium hidden sm:inline"
								:class="step >= index ? 'text-gray-900' : 'text-gray-500'"
							>
								{{ stepItem }}
							</span>
						</div>
						<div
							v-if="index < steps.length - 1"
							class="flex-1 h-0.5 mx-2"
							:class="step > index ? 'bg-green-500' : 'bg-gray-300'"
						></div>
					</div>
				</div>
			</div>

			<!-- Content -->
			<div class="flex-1 overflow-y-auto p-6">
				<!-- Step 1: Select Provider -->
				<div v-if="step === 0">
					<h4 class="font-semibold mb-4 text-lg">Select a Service Provider</h4>

					<div v-if="providersResource.loading" class="flex justify-center py-8">
						<div
							class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"
						></div>
					</div>

					<div v-else class="space-y-3">
						<label
							v-for="provider in providersResource.data"
							:key="provider.name"
							class="flex items-center p-4 border-2 rounded-lg cursor-pointer transition-all"
							:class="
								selectedProvider === provider.name
									? 'border-blue-600 bg-blue-50'
									: 'border-gray-200 hover:border-gray-300'
							"
						>
							<input
								type="radio"
								name="provider"
								:value="provider.name"
								v-model="selectedProvider"
								class="w-4 h-4 text-blue-600"
							/>
							<div class="ml-3 flex-1">
								<div class="font-medium">{{ provider.provider_name }}</div>
								<div v-if="provider.designation" class="text-sm text-gray-500">
									{{ provider.designation }}
								</div>
							</div>
							<div
								v-if="provider.is_default"
								class="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded"
							>
								Recommended
							</div>
						</label>
					</div>
				</div>

				<!-- Step 2: Select Date -->
				<div v-if="step === 1">
					<h4 class="font-semibold mb-4 text-lg">Select Date</h4>

					<div v-if="slotsResource.loading" class="flex justify-center py-8">
						<div
							class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"
						></div>
					</div>

					<div v-else class="flex justify-center">
						<!-- VueDatePicker in inline mode -->
						<VueDatePicker
							v-model="selectedDate"
							:inline="true"
							:enable-time-picker="false"
							:disabled-dates="disabledDates"
							:min-date="new Date()"
							auto-apply
							@update:model-value="handleDateSelect"
							:highlight="highlightedDates"
						/>
					</div>
				</div>

				<!-- Step 3: Select Time Slot -->
				<div v-if="step === 2">
					<h4 class="font-semibold mb-4 text-lg">
						Select Time Slot
						<span v-if="selectedDate" class="text-sm font-normal text-gray-600">
							- {{ formatDate(selectedDate) }}
						</span>
					</h4>

					<div v-if="loadingTimeSlots" class="flex justify-center py-8">
						<div
							class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"
						></div>
					</div>

					<div v-else-if="availableTimeSlots.length === 0" class="text-center py-8">
						<p class="text-gray-600">No available time slots for this date.</p>
						<button @click="step = 1" class="mt-4 text-blue-600 hover:text-blue-700">
							Select different date
						</button>
					</div>

					<div v-else class="space-y-4">
						<div
							v-for="providerSlots in availableTimeSlots"
							:key="providerSlots.provider"
						>
							<h5 class="font-medium text-sm text-gray-700 mb-2">
								{{ providerSlots.provider_name }}
							</h5>
							<div class="grid grid-cols-3 gap-2">
								<button
									v-for="slot in providerSlots.slots"
									:key="slot.slot_id"
									@click="selectTimeSlot(slot, providerSlots.provider)"
									class="p-3 border-2 rounded-lg text-sm transition-all"
									:class="
										selectedSlot?.slot_id === slot.slot_id
											? 'border-blue-600 bg-blue-50 text-blue-900 font-medium'
											: 'border-gray-200 hover:border-gray-300 text-gray-700'
									"
								>
									{{ slot.from_time }}
								</button>
							</div>
						</div>
					</div>
				</div>

				<!-- Step 4: Customer Details -->
				<div v-if="step === 3">
					<h4 class="font-semibold mb-4 text-lg">Your Details</h4>

					<div class="space-y-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">
								Full Name <span class="text-red-500">*</span>
							</label>
							<input
								v-model="customerDetails.full_name"
								type="text"
								required
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
								placeholder="John Doe"
							/>
						</div>

						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">
								Email <span class="text-red-500">*</span>
							</label>
							<input
								v-model="customerDetails.email"
								type="email"
								required
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
								placeholder="john@example.com"
							/>
						</div>

						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">
								Phone <span class="text-red-500">*</span>
							</label>
							<input
								v-model="customerDetails.mobile_no"
								type="tel"
								required
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
								placeholder="+1234567890"
							/>
						</div>

						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">
								Additional Notes (Optional)
							</label>
							<textarea
								v-model="customerDetails.notes"
								rows="3"
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
								placeholder="Any special requests or information..."
							></textarea>
						</div>
					</div>

					<!-- Booking Summary -->
					<div class="mt-6 p-4 bg-gray-50 rounded-lg">
						<h5 class="font-semibold mb-2">Booking Summary</h5>
						<div class="space-y-1 text-sm">
							<div class="flex justify-between">
								<span class="text-gray-600">Service:</span>
								<span class="font-medium">{{ service?.appointment_type }}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-gray-600">Provider:</span>
								<span class="font-medium">{{ selectedProviderName }}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-gray-600">Date:</span>
								<span class="font-medium">{{ formatDate(selectedDate) }}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-gray-600">Time:</span>
								<span class="font-medium">{{ selectedSlot?.from_time }}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-gray-600">Duration:</span>
								<span class="font-medium"
									>{{ service?.default_duration_in_minutes }} min</span
								>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Footer Actions -->
			<div class="bg-gray-50 px-6 py-4 flex justify-between items-center">
				<button
					v-if="step > 0"
					@click="previousStep"
					class="px-4 py-2 text-gray-700 hover:text-gray-900 transition-colors"
				>
					← Back
				</button>
				<div v-else></div>

				<div class="flex gap-3">
					<button
						@click="close"
						class="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors"
					>
						Cancel
					</button>
					<button
						v-if="step < steps.length - 1"
						@click="nextStep"
						:disabled="!canProceed"
						class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
					>
						Next →
					</button>
					<button
						v-else
						@click="submitBooking"
						:disabled="!canSubmit || submitting"
						class="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
					>
						<span v-if="submitting" class="animate-spin">⏳</span>
						<span>{{ submitting ? "Booking..." : "Confirm Booking" }}</span>
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { createResource } from "frappe-ui";
import { VueDatePicker } from "@vuepic/vue-datepicker";
import "@vuepic/vue-datepicker/dist/main.css";

const props = defineProps({
	isVisible: Boolean,
	service: Object,
});

const emit = defineEmits(["close", "success"]);

const steps = ["Provider", "Date", "Time", "Details"];
const step = ref(0);
const submitting = ref(false);

// Step 1: Provider Selection
const selectedProvider = ref(null);
const providersResource = createResource({
	url: "frappoint.frappoint.api.service_provider.get_providers_for_service",
	auto: false,
});

// Step 2 & 3: Date and Time Selection
const selectedDate = ref(null);
const selectedSlot = ref(null);
const selectedSlotProvider = ref(null);
const loadingTimeSlots = ref(false);
const availableTimeSlots = ref([]);

const slotsResource = createResource({
	url: "frappoint.frappoint.api.slot_availability.get_available_time_slots",
	auto: false,
});

// Step 4: Customer Details
const customerDetails = ref({
	full_name: "",
	email: "",
	mobile_no: "",
	notes: "",
});

// Watch for modal visibility
watch(
	() => props.isVisible,
	(visible) => {
		if (visible && props.service) {
			resetForm();
			loadProviders();
			loadAvailableSlots();
		}
	}
);

function resetForm() {
	step.value = 0;
	selectedProvider.value = null;
	selectedDate.value = null;
	selectedSlot.value = null;
	selectedSlotProvider.value = null;
	availableTimeSlots.value = [];
	customerDetails.value = {
		full_name: "",
		email: "",
		mobile_no: "",
		notes: "",
	};
}

function loadProviders() {
	providersResource.fetch({
		service_type: props.service.name,
	});
}

function loadAvailableSlots() {
	console.log("Loading available slots for:", {
		service: props.service?.name,
		provider: selectedProvider.value,
	});

	slotsResource
		.fetch({
			service_type: props.service.name,
			provider: selectedProvider.value,
			days_ahead: 30,
		})
		.then(() => {
			console.log("Slots loaded:", slotsResource.data);

			// Log available dates for debugging
			if (slotsResource.data && Array.isArray(slotsResource.data)) {
				const allDates = new Set();
				slotsResource.data.forEach((providerData) => {
					if (providerData.available_dates) {
						providerData.available_dates.forEach((d) => {
							if (d.slots && d.slots.length > 0) {
								allDates.add(d.date);
							}
						});
					}
				});
				console.log("Available dates:", Array.from(allDates));
			}
		});
}

// Computed properties for VueDatePicker
const disabledDates = computed(() => {
	// Return a function that checks if a date should be disabled
	return (date) => {
		const dateStr = date.toISOString().split("T")[0];
		return !isDateAvailable(dateStr);
	};
});

const highlightedDates = computed(() => {
	// Highlight dates that have available slots
	if (!slotsResource.data || !Array.isArray(slotsResource.data)) return [];

	const dates = [];
	slotsResource.data.forEach((providerData) => {
		if (providerData.available_dates) {
			providerData.available_dates.forEach((d) => {
				if (d.slots && d.slots.length > 0) {
					dates.push(new Date(d.date));
				}
			});
		}
	});

	return dates;
});

function handleDateSelect(date) {
	if (date) {
		const dateStr = typeof date === "string" ? date : date.toISOString().split("T")[0];
		selectDate(dateStr);
	}
}

// Calendar dates computation (keeping for backwards compatibility if needed)
const calendarDates = computed(() => {
	if (!slotsResource.data || !Array.isArray(slotsResource.data)) return [];

	const today = new Date();
	today.setHours(0, 0, 0, 0);

	const dates = [];
	const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
	const lastDay = new Date(today.getFullYear(), today.getMonth() + 2, 0);

	// Add empty cells for days before month start
	for (let i = 0; i < firstDay.getDay(); i++) {
		dates.push(null);
	}

	// Add all days in the range
	const currentDate = new Date(firstDay);
	while (currentDate <= lastDay) {
		const dateStr = currentDate.toISOString().split("T")[0];
		const date = new Date(currentDate);

		// Only add dates that are today or in the future
		if (date >= today) {
			dates.push(dateStr);
		} else {
			dates.push(null); // Past dates as null
		}

		currentDate.setDate(currentDate.getDate() + 1);
	}

	return dates;
});

function isDateAvailable(date) {
	if (!date || !slotsResource.data || !Array.isArray(slotsResource.data)) {
		return false;
	}

	// Check if the date is in the past
	const selectedDate = new Date(date);
	const today = new Date();
	today.setHours(0, 0, 0, 0);

	if (selectedDate < today) {
		return false;
	}

	// Check if any provider has available slots for this date
	for (const providerData of slotsResource.data) {
		if (!providerData.available_dates || !Array.isArray(providerData.available_dates)) {
			continue;
		}

		const hasSlots = providerData.available_dates.some(
			(d) => d.date === date && d.slots && d.slots.length > 0
		);

		if (hasSlots) {
			return true;
		}
	}

	return false;
}

function selectDate(date) {
	selectedDate.value = date;
	selectedSlot.value = null;
	loadTimeSlotsForDate(date);
}

function loadTimeSlotsForDate(date) {
	if (!slotsResource.data) return;

	loadingTimeSlots.value = true;
	availableTimeSlots.value = [];

	setTimeout(() => {
		const slots = [];

		for (const providerData of slotsResource.data) {
			const dateData = providerData.available_dates?.find((d) => d.date === date);
			if (dateData && dateData.slots?.length > 0) {
				slots.push({
					provider: providerData.provider,
					provider_name: providerData.provider_name,
					slots: dateData.slots,
				});
			}
		}

		availableTimeSlots.value = slots;
		loadingTimeSlots.value = false;
	}, 300);
}

function selectTimeSlot(slot, provider) {
	selectedSlot.value = slot;
	selectedSlotProvider.value = provider;
}

const selectedProviderName = computed(() => {
	if (!selectedSlotProvider.value) return "Any Provider";
	const providerData = slotsResource.data?.find(
		(p) => p.provider === selectedSlotProvider.value
	);
	return providerData?.provider_name || selectedSlotProvider.value;
});

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

const canProceed = computed(() => {
	if (step.value === 0) return true; // Can always proceed from provider selection
	if (step.value === 1) return selectedDate.value !== null;
	if (step.value === 2) return selectedSlot.value !== null;
	return false;
});

const canSubmit = computed(() => {
	return (
		customerDetails.value.full_name &&
		customerDetails.value.email &&
		customerDetails.value.mobile_no &&
		selectedSlot.value
	);
});

function nextStep() {
	if (step.value === 0 && selectedProvider.value !== null) {
		// Reload slots for specific provider
		loadAvailableSlots();
	}
	if (canProceed.value && step.value < steps.length - 1) {
		step.value++;
	}
}

function previousStep() {
	if (step.value > 0) {
		step.value--;
	}
}

async function submitBooking() {
	if (!canSubmit.value || submitting.value) return;

	submitting.value = true;

	try {
		// TODO: Replace with actual API call to create appointment
		const response = await fetch("/api/method/frappe.client.insert", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify({
				doc: {
					doctype: "Service Appointment",
					appointment_type: props.service.name,
					appointment_provider: selectedSlotProvider.value,
					appointment_date: selectedDate.value,
					start_time: selectedSlot.value.from_time,
					end_time: selectedSlot.value.to_time,
					duration: props.service.default_duration_in_minutes,
					full_name: customerDetails.value.full_name,
					email: customerDetails.value.email,
					mobile_no: customerDetails.value.mobile_no,
					notes: customerDetails.value.notes,
					selected_slot_ids: JSON.stringify([selectedSlot.value.slot_id]),
					status: "Open",
					source: "Portal",
				},
			}),
		});

		if (response.ok) {
			emit("success");
			close();
		} else {
			throw new Error("Failed to create appointment");
		}
	} catch (error) {
		console.error("Booking error:", error);
		alert("Failed to create booking. Please try again.");
	} finally {
		submitting.value = false;
	}
}

function close() {
	emit("close");
}
</script>

<style scoped>
/* Custom VueDatePicker styling */
:deep(.dp__theme_light) {
	--dp-primary-color: #2563eb;
	--dp-primary-text-color: #fff;
	--dp-secondary-color: #dbeafe;
	--dp-border-color: #e5e7eb;
	--dp-menu-border-color: #e5e7eb;
	--dp-border-color-hover: #d1d5db;
	--dp-disabled-color: #f3f4f6;
	--dp-scroll-bar-background: #f3f4f6;
	--dp-scroll-bar-color: #9ca3af;
	--dp-success-color: #10b981;
	--dp-success-color-disabled: #d1fae5;
	--dp-icon-color: #6b7280;
	--dp-danger-color: #ef4444;
	--dp-highlight-color: rgba(37, 99, 235, 0.1);
}

:deep(.dp__calendar) {
	font-family: inherit;
}

:deep(.dp__calendar_header_item) {
	font-weight: 600;
	color: #4b5563;
}

:deep(.dp__cell_inner) {
	border-radius: 0.5rem;
}

:deep(.dp__cell_disabled) {
	color: #d1d5db !important;
	background-color: #f9fafb !important;
	cursor: not-allowed;
}

:deep(.dp__today) {
	border: 2px solid #2563eb;
}

:deep(.dp__active_date) {
	background-color: #2563eb !important;
	color: white !important;
}
</style>
