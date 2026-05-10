<template>
	<div class="min-h-[500px] flex flex-col">
		<div class="flex items-center justify-center gap-4 mb-8">
			<div v-for="step in 3" :key="step" class="flex items-center">
				<div
					:class="[
						'size-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors',
						currentStep === step
							? 'bg-primary text-white'
							: 'bg-slate-100 text-slate-400',
					]"
				>
					{{ step }}
				</div>
				<div v-if="step < 3" class="w-12 h-0.5 bg-slate-100 mx-2"></div>
			</div>
		</div>

		<div class="flex-1 overflow-y-auto px-2">
			<div
				v-if="currentStep === 1"
				class="animate-in fade-in slide-in-from-right-4 duration-300"
			>
				<GuestDetails v-model="tempGuest" />
			</div>
			<div
				v-if="currentStep === 2"
				class="animate-in fade-in slide-in-from-right-4 duration-300"
			>
				<ServiceSelection v-model="tempGuest" />
			</div>
			<div
				v-if="currentStep === 3"
				class="animate-in fade-in slide-in-from-right-4 duration-300"
			>
				<SlotSelection
					:date="tempGuest.date"
					@update:date="tempGuest.date = $event"
					:slot="tempGuest.slot"
					@update:slot="tempGuest.slot = $event"
					:provider="tempGuest.provider"
					@update:provider="tempGuest.provider = $event"
					:available-dates="availableDates.data"
					:dates-loading="availableDates.loading"
					:available-slots="availableSlots.data"
					:slots-loading="availableSlots.loading"
				/>
			</div>
		</div>

		<div class="mt-8 pt-6 border-t border-slate-100 flex items-center justify-between">
			<div>
				<button
					v-if="currentStep > 1"
					@click="currentStep--"
					class="px-4 py-2 text-sm font-bold text-slate-600 hover:bg-slate-50 rounded-lg transition-colors flex items-center gap-2"
				>
					<span class="material-symbols-outlined text-[18px]">arrow_back</span>
					Back
				</button>
			</div>

			<div class="flex items-center gap-3">
				<button
					@click="$emit('close')"
					class="px-4 py-2 text-sm font-bold text-slate-400 hover:text-slate-600 transition-colors"
				>
					Cancel
				</button>

				<button
					@click="handleNext"
					class="px-8 py-2.5 bg-slate-900 hover:bg-black text-white rounded-xl text-sm font-bold transition-all flex items-center gap-2 shadow-lg shadow-slate-200"
				>
					<span>{{ currentStep === 3 ? "Finish & Add" : "Next Step" }}</span>
					<span class="material-symbols-outlined text-[18px]">
						{{ currentStep === 3 ? "check_circle" : "arrow_forward" }}
					</span>
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import GuestDetails from "./steps/GuestDetails.vue";
import ServiceSelection from "./steps/ServiceSelection.vue";
import SlotSelection from "./steps/SlotSelection.vue";
import { createResource } from "frappe-ui";
import { useBookingStore } from "@/stores/bookingStore";
import { flattenSlotsByProvider } from "@/utils/slotTransformation";

const emit = defineEmits(["close", "save"]);
const bookingStore = useBookingStore();

const selectedGuestIndex = ref(null);
const currentStep = ref(1);

// 1. Initialize the temp guest object
const tempGuest = ref({
	guest_full_name: "",
	guest_email: "",
	guest_mobile_no: "",
	price_id: null,
	appointment_type: "",
	service: "",
	duration: 0,
	amount: 0,
	currency: "",
	date: null,
	slot: null,
	provider: null,
});

watch(
	tempGuest,
	(newVal) => {
		if (selectedGuestIndex.value !== null) {
			bookingStore.updateGuest(selectedGuestIndex.value, newVal);
		}
	},
	{ deep: true }
);

// 2. Resource: Fetch Available Dates (THIS WAS MISSING)
const availableDates = createResource({
	url: "frappoint.frappoint.api.slot_availability.get_available_dates",
	auto: false,
});

// 3. Resource: Fetch Available Slots
const availableSlots = createResource({
	url: "frappoint.frappoint.api.slot_availability.get_available_time_slots",
	auto: false,
	transform: (data) => flattenSlotsByProvider(data),
});

// Watch for Service changes -> load dates
watch(
	() => [tempGuest.value.appointment_type, tempGuest.value.duration],
	([type, duration]) => {
		if (type && duration) {
			availableDates.submit({ service_type: type, duration });
		}
	}
);

// 4. Watcher for Dates (Triggers when Step 2 selection is made)
watch(
	() => [tempGuest.value.appointment_type, tempGuest.value.duration],
	([type, duration]) => {
		if (type && duration) {
			availableDates.submit({
				service_type: type,
				duration: duration,
			});
		}
	}
);

// 5. Watcher for Slots (Triggers when a date is selected in Step 3)
watch(
	() => tempGuest.value.date,
	(newDate) => {
		if (newDate) {
			availableSlots.submit({
				service_type: tempGuest.value.appointment_type,
				duration: tempGuest.value.duration,
				date: newDate,
			});
		}
	}
);

// watch(
//   () => bookingStore.customer,
//   (newCustomer) => {
//     if (newCustomer.fullName && !tempGuest.value.full_name) {
//       tempGuest.value.full_name = newCustomer.fullName;
//       tempGuest.value.mobile_no = newCustomer.mobileNo;
//       tempGuest.value.email = newCustomer.email;
//     }
//   },
//   { immediate: true }
// );

function handleNext() {
	if (currentStep.value < 3) {
		currentStep.value++;
		return;
	}

	if (!tempGuest.value.slot) {
		alert("Please select a time slot.");
		return;
	}

	if (selectedGuestIndex.value === null) {
		bookingStore.addGuest({ ...tempGuest.value });
		selectedGuestIndex.value = bookingStore.guests.length - 1;
	} else {
		bookingStore.updateGuest(selectedGuestIndex.value, { ...tempGuest.value });
	}

	// Reset modal for next guest
	tempGuest.value = {
		guest_full_name: "",
		guest_email: "",
		guest_mobile_no: "",
		price_id: null,
		appointment_type: "",
		service: "",
		duration: 0,
		amount: 0,
		currency: "KES",
		date: null,
		slot: null,
		provider: null,
	};
	currentStep.value = 1;
	selectedGuestIndex.value = null;
	emit("close");
}

function editGuest(index) {
	selectedGuestIndex.value = index;
	tempGuest.value = { ...bookingStore.guests[index] };
	currentStep.value = 1;
}

defineExpose({
	editGuest,
});
</script>
