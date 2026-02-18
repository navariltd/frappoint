<template>
	<div class="flex flex-col lg:flex-row gap-6 lg:gap-8 w-full p-6 md:p-8">
		<!-- Left Column - Your Information Form -->
		<div class="w-full lg:w-2/3">
			<div class="flex items-center justify-between mb-6">
				<h2 class="text-xl font-bold text-gray-900 dark:text-white">Your Information</h2>
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
						{{ booking.draft.numberOfGuests }}
						{{ booking.draft.numberOfGuests === 1 ? "Guest" : "Guests" }}
					</span>
				</div>
			</div>

			<form class="space-y-6">
				<!-- Primary Guest (Contact Person) -->
				<div
					class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6"
				>
					<div class="flex items-center gap-2 mb-4">
						<div
							class="flex items-center justify-center w-6 h-6 bg-primary/10 dark:bg-primary/20 text-primary dark:text-teal-400 rounded-full text-xs font-bold"
						>
							1
						</div>
						<h3 class="text-base font-bold text-gray-900 dark:text-white">
							Primary Guest (Contact Person)
						</h3>
					</div>

					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<div class="space-y-2">
							<label
								class="text-sm font-semibold text-gray-700 dark:text-gray-300"
								for="full-name"
							>
								Full Name
							</label>
							<input
								id="full-name"
								v-model="primaryFullName"
								:disabled="isLoggedIn"
								class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all disabled:bg-gray-50 disabled:cursor-not-allowed"
								type="text"
								placeholder="John Doe"
							/>
						</div>
						<div class="space-y-2">
							<label
								class="text-sm font-semibold text-gray-700 dark:text-gray-300"
								for="email"
							>
								Email Address
							</label>
							<input
								id="email"
								v-model="primaryEmail"
								:disabled="isLoggedIn"
								class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all disabled:bg-gray-50 disabled:cursor-not-allowed"
								type="email"
								placeholder="john@example.com"
							/>
						</div>
					</div>
					<div class="space-y-2 mt-4">
						<label
							class="text-sm font-semibold text-gray-700 dark:text-gray-300"
							for="phone"
						>
							Phone Number
						</label>
						<input
							id="phone"
							v-model="primaryMobileNo"
							:disabled="isLoggedIn"
							class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all disabled:bg-gray-50 disabled:cursor-not-allowed"
							type="tel"
							placeholder="+1 (555) 000-0000"
						/>
					</div>
				</div>

				<!-- Additional Guests -->
				<div
					v-for="(guest, index) in additionalGuests"
					:key="index"
					class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden"
				>
					<button
						type="button"
						@click="toggleGuest(index + 1)"
						class="w-full flex items-center justify-between p-6 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
					>
						<div class="flex items-center gap-2">
							<div
								class="flex items-center justify-center w-6 h-6 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-xs font-bold"
							>
								{{ index + 2 }}
							</div>
							<h3 class="text-base font-bold text-gray-900 dark:text-white">
								Guest {{ index + 2 }}
							</h3>
							<span
								v-if="guest.full_name"
								class="text-sm text-gray-500 dark:text-gray-400"
							>
								- {{ guest.full_name }}
							</span>
						</div>
						<svg
							class="w-5 h-5 text-gray-400 transition-transform"
							:class="{ 'rotate-180': expandedGuests[index + 1] }"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M19 9l-7 7-7-7"
							/>
						</svg>
					</button>

					<div
						v-show="expandedGuests[index + 1]"
						class="px-6 pb-6 border-t border-gray-100 dark:border-gray-700"
					>
						<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
							<div class="space-y-2">
								<label
									class="text-sm font-semibold text-gray-700 dark:text-gray-300"
									:for="`guest-${index}-name`"
								>
									Full Name
								</label>
								<input
									:id="`guest-${index}-name`"
									:value="guest.full_name"
									@input="
										updateGuestField(
											index + 1,
											'full_name',
											$event.target.value
										)
									"
									class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all"
									type="text"
									placeholder="Jane Smith"
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
									@input="
										updateGuestField(index + 1, 'email', $event.target.value)
									"
									class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all"
									type="email"
									placeholder="jane@example.com"
								/>
							</div>
						</div>
						<div class="space-y-2 mt-4">
							<label
								class="text-sm font-semibold text-gray-700 dark:text-gray-300"
								:for="`guest-${index}-phone`"
							>
								Phone Number
							</label>
							<input
								:id="`guest-${index}-phone`"
								:value="guest.mobile_no"
								@input="
									updateGuestField(index + 1, 'mobile_no', $event.target.value)
								"
								class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all"
								type="tel"
								placeholder="+1 (555) 000-0000"
							/>
						</div>
					</div>
				</div>

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
const expandedGuests = ref({});

// Initialize guests when component mounts
onMounted(() => {
	if (!booking.draft.guests || booking.draft.guests.length === 0) {
		booking.initializeGuests();
	}

	// Auto-expand first additional guest if exists
	if (booking.draft.numberOfGuests > 1) {
		expandedGuests.value[1] = true;
	}
});

// Primary guest computed properties with two-way sync
const primaryFullName = computed({
	get: () => booking.draft.fullName,
	set: (value) => {
		booking.setFullName(value);
		booking.updateGuest(0, "full_name", value);
	},
});

const primaryEmail = computed({
	get: () => booking.draft.email,
	set: (value) => {
		booking.setEmail(value);
		booking.updateGuest(0, "email", value);
	},
});

const primaryMobileNo = computed({
	get: () => booking.draft.mobileNo,
	set: (value) => {
		booking.setMobileNo(value);
		booking.updateGuest(0, "mobile_no", value);
	},
});

// Additional guests (excluding primary)
const additionalGuests = computed(() => {
	if (!booking.draft.guests || !Array.isArray(booking.draft.guests)) {
		return [];
	}
	return booking.draft.guests.slice(1);
});

// Toggle guest form expansion
function toggleGuest(index) {
	expandedGuests.value[index] = !expandedGuests.value[index];
}

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
