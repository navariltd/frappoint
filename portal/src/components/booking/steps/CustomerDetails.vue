<template>
	<div class="flex flex-col lg:flex-row gap-6 lg:gap-8 w-full p-6 md:p-8">
		<!-- Left Column - Your Information Form -->
		<div class="w-full lg:w-2/3">
			<h2 class="text-xl font-bold text-gray-900 dark:text-white mb-6">Your Information</h2>
			<form class="space-y-6">
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					<div class="space-y-2">
						<label
							class="text-sm font-semibold text-gray-700 dark:text-gray-300"
							for="full-name"
						>
							Full Name
						</label>
						<input
							id="full-name"
							v-model="localCustomer"
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
							v-model="localEmail"
							:disabled="isLoggedIn"
							class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all disabled:bg-gray-50 disabled:cursor-not-allowed"
							type="email"
							placeholder="john@example.com"
						/>
					</div>
				</div>
				<div class="space-y-2">
					<label
						class="text-sm font-semibold text-gray-700 dark:text-gray-300"
						for="phone"
					>
						Phone Number
					</label>
					<input
						id="phone"
						v-model="localMobileNo"
						:disabled="isLoggedIn"
						class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all disabled:bg-gray-50 disabled:cursor-not-allowed"
						type="tel"
						placeholder="+1 (555) 000-0000"
					/>
				</div>
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
						v-model="localNotes"
						class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all resize-none"
						placeholder="Anything we should know before your arrival?"
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
import { computed, ref, watch } from "vue";

const props = defineProps({
	isLoggedIn: {
		type: Boolean,
		default: false,
	},
});

const booking = useBookingStore();

// Local state for form inputs
const localCustomer = ref(booking.draft.customer || "");
const localEmail = ref(booking.draft.email || "");
const localMobileNo = ref(booking.draft.mobileNo || "");
const localNotes = ref(booking.draft.notes || "");

// Watch local state and update store
watch(localCustomer, (value) => booking.setCustomer(value));
watch(localEmail, (value) => booking.setEmail(value));
watch(localMobileNo, (value) => booking.setMobileNo(value));
watch(localNotes, (value) => (booking.draft.notes = value));

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
