<template>
	<div class="flex flex-col lg:flex-row gap-6 lg:gap-8 w-full p-6 md:p-8">
		<!-- Left Column - Your Information Form -->
		<div class="w-full lg:w-2/3">
			<!-- Customer Details Section -->
			<div class="mb-6">
				<h2 class="text-xl font-bold text-gray-900 dark:text-white mb-6">
					Your Information
				</h2>

				<div
					class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6"
				>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<div class="space-y-2">
							<label
								class="text-sm font-semibold text-gray-700 dark:text-gray-300"
								for="customer-name"
							>
								Full Name
								<span class="text-red-500">*</span>
							</label>
							<input
								id="customer-name"
								v-model="booking.draft.fullName"
								:disabled="isLoggedIn"
								class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all disabled:bg-gray-50 disabled:cursor-not-allowed"
								type="text"
								placeholder="John Doe"
								required
							/>
						</div>
						<div class="space-y-2">
							<label
								class="text-sm font-semibold text-gray-700 dark:text-gray-300"
								for="customer-email"
							>
								Email Address
								<span class="text-red-500">*</span>
							</label>
							<input
								id="customer-email"
								v-model="booking.draft.email"
								:disabled="isLoggedIn"
								type="email"
								class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all disabled:bg-gray-50 disabled:cursor-not-allowed"
								placeholder="john@example.com"
								required
							/>
						</div>
					</div>
					<div class="space-y-2 mt-4">
						<label
							class="text-sm font-semibold text-gray-700 dark:text-gray-300"
							for="customer-phone"
						>
							Phone Number
							<span class="text-red-500">*</span>
						</label>
						<input
							id="customer-phone"
							v-model="booking.draft.mobileNo"
							:disabled="isLoggedIn"
							type="tel"
							class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all disabled:bg-gray-50 disabled:cursor-not-allowed"
							placeholder="+1 (555) 000-0000"
							required
						/>
					</div>
				</div>
			</div>

			<!-- Guest Forms Section -->
			<div class="mb-6">
				<div class="flex items-center justify-between mb-6">
					<h2 class="text-xl font-bold text-gray-900 dark:text-white">
						Guest Information
					</h2>
					<div
						class="flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 rounded-lg"
					>
						<svg
							class="w-4 h-4 text-gray-600 dark:text-gray-300"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
							/>
						</svg>
						<span class="text-sm font-semibold text-gray-700 dark:text-gray-300">
							{{ booking.draft.minGuests }}
							{{ booking.draft.minGuests === 1 ? "Guest" : "Guests" }} Required
						</span>
					</div>
				</div>

				<div class="space-y-4">
					<!-- Guest Forms -->
					<div
						v-for="(guest, index) in allGuests"
						:key="index"
						class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6"
					>
						<div class="flex items-center gap-2 mb-4">
							<div
								class="flex items-center justify-center w-6 h-6 bg-primary/10 dark:bg-primary/20 text-primary dark:text-teal-400 rounded-full text-xs font-bold"
							>
								{{ index + 1 }}
							</div>
							<h3 class="text-base font-bold text-gray-900 dark:text-white">
								Guest {{ index + 1 }}
							</h3>
						</div>

						<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
							<div class="space-y-2">
								<label
									class="text-sm font-semibold text-gray-700 dark:text-gray-300"
									:for="`guest-${index}-name`"
								>
									Full Name
									<span class="text-red-500">*</span>
								</label>
								<input
									:id="`guest-${index}-name`"
									:value="guest.full_name"
									@input="
										updateGuestField(index, 'full_name', $event.target.value)
									"
									class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all"
									type="text"
									placeholder="Guest Name"
									required
								/>
							</div>
							<div class="space-y-2">
								<label
									class="text-sm font-semibold text-gray-700 dark:text-gray-300"
									:for="`guest-${index}-email`"
								>
									Email Address
									<span class="text-gray-400 font-normal text-xs"
										>(Optional)</span
									>
								</label>
								<input
									:id="`guest-${index}-email`"
									:value="guest.email"
									@input="updateGuestField(index, 'email', $event.target.value)"
									type="email"
									class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all"
									placeholder="guest@example.com"
								/>
							</div>
						</div>
						<div class="space-y-2 mt-4">
							<label
								class="text-sm font-semibold text-gray-700 dark:text-gray-300"
								:for="`guest-${index}-phone`"
							>
								Phone Number
								<span class="text-gray-400 font-normal text-xs">(Optional)</span>
							</label>
							<input
								:id="`guest-${index}-phone`"
								:value="guest.mobile_no"
								@input="updateGuestField(index, 'mobile_no', $event.target.value)"
								type="tel"
								class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all"
								placeholder="+1 (555) 000-0000"
							/>
						</div>
					</div>
				</div>
			</div>

			<form class="space-y-6">
				<!-- Additional Notes -->
				<div class="space-y-2">
					<label
						class="text-sm font-semibold text-gray-700 dark:text-gray-300"
						for="notes"
					>
						Additional Notes
						<span class="text-gray-400 font-normal text-xs">(Optional)</span>
					</label>
					<textarea
						id="notes"
						v-model="booking.draft.notes"
						class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all resize-none"
						placeholder="Any special requests or allergies we should know about?"
						rows="4"
					></textarea>
				</div>
			</form>
		</div>

		<!-- Right Column - Booking Summary -->
		<aside class="w-full lg:w-1/3 space-y-6">
			<div
				class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 p-6"
			>
				<h3 class="text-lg font-bold text-gray-900 dark:text-white mb-4">
					Booking Summary
				</h3>
				<div class="space-y-4">
					<div class="flex gap-4">
						<div
							class="flex-shrink-0 w-12 h-12 bg-teal-50 dark:bg-teal-900/30 rounded-xl flex items-center justify-center text-primary dark:text-teal-400"
						>
							<svg
								class="w-6 h-6"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
								/>
							</svg>
						</div>
						<div>
							<p class="text-sm font-bold text-gray-900 dark:text-white">
								{{ booking.draft.serviceType || "Service" }}
							</p>
							<p class="text-xs text-gray-500 dark:text-gray-400">
								{{ serviceDuration }}
							</p>
						</div>
					</div>
					<div class="border-t border-gray-100 dark:border-gray-700 pt-4 space-y-3">
						<div class="flex items-center gap-3 text-gray-600 dark:text-gray-300">
							<svg
								class="w-5 h-5 opacity-70"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
								/>
							</svg>
							<span class="text-sm">{{ formattedDate }}</span>
						</div>
						<div class="flex items-center gap-3 text-gray-600 dark:text-gray-300">
							<svg
								class="w-5 h-5 opacity-70"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
								/>
							</svg>
							<span class="text-sm">{{ formattedTime }}</span>
						</div>
						<div class="flex items-center gap-3 text-gray-600 dark:text-gray-300">
							<svg
								class="w-5 h-5 opacity-70"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
								/>
							</svg>
							<span class="text-sm">{{ providerName }}</span>
						</div>
					</div>
					<div class="border-t border-gray-100 dark:border-gray-700 pt-4">
						<div class="flex items-center justify-between">
							<span class="text-sm text-gray-500 dark:text-gray-400">Subtotal</span>
							<span class="text-sm font-medium text-gray-900 dark:text-white">{{
								formatCurrency(booking.draft.price, booking.draft.currency)
							}}</span>
						</div>
						<div class="flex items-center justify-between mt-1">
							<span class="text-sm text-gray-500 dark:text-gray-400">Tax</span>
							<span class="text-sm font-medium text-gray-900 dark:text-white">{{
								formatCurrency(0, booking.draft.currency)
							}}</span>
						</div>
						<div class="flex items-center justify-between mt-4 text-lg font-bold">
							<span class="text-gray-900 dark:text-white">Total</span>
							<span class="text-primary dark:text-teal-400">{{
								formatCurrency(booking.draft.price, booking.draft.currency)
							}}</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-primary/5 dark:bg-primary/10 border border-primary/20 rounded-2xl p-6">
				<div class="flex items-center gap-3 mb-2">
					<svg
						class="w-6 h-6 text-primary dark:text-teal-400"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
					<h4 class="font-bold text-gray-900 dark:text-white">Need help?</h4>
				</div>
				<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
					If you have questions about your booking, feel free to contact us.
				</p>
				<a
					class="text-sm font-bold text-primary dark:text-teal-400 hover:underline"
					href="#"
				>
					Contact Support
				</a>
			</div>
		</aside>
	</div>
</template>

<script setup>
import { useBookingStore } from "@/stores/bookingStore";
import { formatCurrency } from "@/utils";
import { computed, ref, watch, onMounted } from "vue";

const props = defineProps({
	isLoggedIn: {
		type: Boolean,
		default: false,
	},
});

const booking = useBookingStore();

// Initialize guests when component mounts
onMounted(() => {
	// Ensure guests are initialized based on min_guests
	const requiredGuests = booking.draft.minGuests || 1;
	if (!booking.draft.guests || booking.draft.guests.length === 0) {
		booking.setNumberOfGuests(requiredGuests);
	} else if (booking.draft.guests.length < requiredGuests) {
		// Ensure we have at least the minimum number of guests
		booking.setNumberOfGuests(requiredGuests);
	}
});

// All guests to display (based on min_guests)
const allGuests = computed(() => {
	if (!booking.draft.guests || !Array.isArray(booking.draft.guests)) {
		return [];
	}
	return booking.draft.guests;
});

// Watch customer details and sync to first guest (billing contact)
watch(
	() => booking.draft.fullName,
	(newValue) => {
		if (booking.draft.guests && booking.draft.guests[0]) {
			booking.draft.guests[0].full_name = newValue;
		}
	}
);

watch(
	() => booking.draft.email,
	(newValue) => {
		if (booking.draft.guests && booking.draft.guests[0]) {
			booking.draft.guests[0].email = newValue;
		}
	}
);

watch(
	() => booking.draft.mobileNo,
	(newValue) => {
		if (booking.draft.guests && booking.draft.guests[0]) {
			booking.draft.guests[0].mobile_no = newValue;
		}
	}
);

// Update guest field
function updateGuestField(index, field, value) {
	booking.updateGuest(index, field, value);
}

// Computed properties for display
const formattedDate = computed(() => {
	if (!booking.draft.date) return "Not selected";
	const date = new Date(booking.draft.date);
	return date.toLocaleDateString("en-US", {
		weekday: "long",
		year: "numeric",
		month: "long",
		day: "numeric",
	});
});

const formattedTime = computed(() => {
	if (!booking.draft.slot?.start_time) return "Not selected";
	return formatTime(booking.draft.slot.start_time);
});

const providerName = computed(() => {
	return booking.draft.slot?.provider_name || "Not assigned";
});

const serviceDuration = computed(() => {
	if (!booking.draft.slot) return "";
	const start = booking.draft.slot.start_time;
	const end = booking.draft.slot.end_time;
	if (!start || !end) return "";

	const startDate = new Date(`2000-01-01T${start}`);
	const endDate = new Date(`2000-01-01T${end}`);
	const diffMs = endDate - startDate;
	const diffMins = Math.round(diffMs / 60000);
	return `${diffMins} minutes`;
});

function formatTime(time) {
	if (!time) return "";
	const [hours, minutes] = time.split(":");
	const hour = parseInt(hours);
	const ampm = hour >= 12 ? "PM" : "AM";
	const displayHour = hour % 12 || 12;
	return `${displayHour}:${minutes} ${ampm}`;
}
</script>
