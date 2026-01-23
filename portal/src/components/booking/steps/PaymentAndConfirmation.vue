<template>
	<div class="flex flex-col h-full">
		<div class="flex flex-col lg:flex-row gap-6 lg:gap-8 w-full p-6 md:p-8 flex-1">
			<!-- Left Column - Payment Form -->
			<div class="w-full lg:flex-1">
				<h2 class="text-xl font-bold text-gray-900 dark:text-white mb-6">
					Payment Method
				</h2>

				<div class="relative flex py-5 items-center mb-8">
					<div class="flex-grow border-t border-gray-200 dark:border-gray-700"></div>
					<span
						class="flex-shrink mx-4 text-gray-400 text-xs font-bold uppercase tracking-wider"
						>Pay with card</span
					>
					<div class="flex-grow border-t border-gray-200 dark:border-gray-700"></div>
				</div>

				<form class="space-y-6">
					<div>
						<label
							class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2"
							for="cardholder-name"
						>
							Cardholder Name
						</label>
						<input
							id="cardholder-name"
							v-model="cardholderName"
							class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all"
							placeholder="Jane Doe"
							type="text"
						/>
					</div>

					<div>
						<label
							class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2"
							for="card-number"
						>
							Card Number
						</label>
						<div class="relative">
							<input
								id="card-number"
								v-model="cardNumber"
								class="w-full px-4 py-3 pr-12 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all"
								placeholder="0000 0000 0000 0000"
								type="tel"
							/>
							<div class="absolute inset-y-0 right-0 flex items-center pr-4">
								<svg
									class="w-5 h-5 text-gray-400"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
									/>
								</svg>
							</div>
						</div>
					</div>

					<div class="grid grid-cols-2 gap-4">
						<div>
							<label
								class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2"
								for="expiry"
							>
								Expiry Date
							</label>
							<input
								id="expiry"
								v-model="expiryDate"
								class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all"
								placeholder="MM / YY"
								type="text"
							/>
						</div>
						<div>
							<label
								class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2"
								for="cvc"
							>
								CVC
							</label>
							<input
								id="cvc"
								v-model="cvc"
								class="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all"
								placeholder="123"
								type="tel"
							/>
						</div>
					</div>

					<div class="flex items-center gap-3 pt-2">
						<input
							id="save-card"
							v-model="saveCard"
							class="rounded text-primary focus:ring-primary w-4 h-4 border-gray-300"
							type="checkbox"
						/>
						<label class="text-sm text-gray-600 dark:text-gray-400" for="save-card"
							>Save card for future bookings</label
						>
					</div>
				</form>
			</div>

			<!-- Right Column - Booking Summary -->
			<aside class="w-full lg:w-80 xl:w-96 flex-shrink-0">
				<div
					class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 sticky top-24"
				>
					<h2 class="text-lg font-bold text-gray-900 dark:text-white mb-6">
						Booking Summary
					</h2>

					<div class="space-y-6 pb-6 border-b border-gray-100 dark:border-gray-800">
						<!-- Service Info -->
						<div class="flex gap-4">
							<div
								class="w-16 h-16 rounded-xl bg-gray-100 dark:bg-gray-800 flex-shrink-0 flex items-center justify-center"
							>
								<svg
									class="w-8 h-8 text-primary"
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
								<h3 class="font-bold text-gray-900 dark:text-white leading-tight">
									{{ booking.draft.serviceType || "Service" }}
								</h3>
								<p class="text-sm text-gray-500 dark:text-gray-400">
									{{ serviceDuration }}
								</p>
								<p class="text-sm font-medium text-primary mt-1">
									{{
										formatCurrency(booking.draft.price, booking.draft.currency)
									}}
								</p>
							</div>
						</div>

						<!-- Appointment Details -->
						<div class="space-y-3">
							<div class="flex items-center gap-3 text-gray-600 dark:text-gray-400">
								<svg
									class="w-5 h-5"
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
							<div class="flex items-center gap-3 text-gray-600 dark:text-gray-400">
								<svg
									class="w-5 h-5"
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
							<div class="flex items-center gap-3 text-gray-600 dark:text-gray-400">
								<svg
									class="w-5 h-5"
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
					</div>

					<!-- Price Breakdown -->
					<div class="py-6 space-y-3">
						<div class="flex justify-between text-sm">
							<span class="text-gray-500 dark:text-gray-400">Subtotal</span>
							<span class="font-semibold text-gray-900 dark:text-white">{{
								formatCurrency(booking.draft.price, booking.draft.currency)
							}}</span>
						</div>
						<div class="flex justify-between text-sm">
							<span class="text-gray-500 dark:text-gray-400"
								>Tax ({{ taxRate }}%)</span
							>
							<span class="font-semibold text-gray-900 dark:text-white">{{
								formatCurrency(taxAmount, booking.draft.currency)
							}}</span>
						</div>
						<div
							class="pt-3 border-t border-gray-100 dark:border-gray-800 flex justify-between items-baseline"
						>
							<span class="text-lg font-bold text-gray-900 dark:text-white"
								>Total</span
							>
							<span class="text-2xl font-extrabold text-primary">{{
								formatCurrency(totalAmount, booking.draft.currency)
							}}</span>
						</div>
					</div>
				</div>
			</aside>
		</div>

		<!-- Buttons Section -->
		<div
			class="px-6 md:px-8 pb-6 md:pb-8 flex items-center justify-between border-t border-gray-100 pt-6"
		>
			<button
				@click="emit('back')"
				class="px-6 py-3 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-semibold hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				type="button"
			>
				Back
			</button>
			<button
				:disabled="!canProceed"
				@click="emit('submit')"
				class="px-8 py-3 rounded-lg bg-primary hover:bg-primary-dark text-white font-semibold shadow-lg shadow-primary/30 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
				type="button"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
					/>
				</svg>
				Confirm and Pay
			</button>
		</div>
	</div>
</template>

<script setup>
import { useBookingStore } from "@/stores/bookingStore";
import { formatCurrency } from "@/utils";
import { computed, ref } from "vue";

const props = defineProps({
	canProceed: Boolean,
});

const emit = defineEmits(["back", "submit"]);

const booking = useBookingStore();

// Form fields
const cardholderName = ref("");
const cardNumber = ref("");
const expiryDate = ref("");
const cvc = ref("");
const saveCard = ref(false);

// Tax calculation
const taxRate = ref(8);
const taxAmount = computed(() => {
	const price = parseFloat(booking.draft.price) || 0;
	return (price * taxRate.value) / 100;
});

const totalAmount = computed(() => {
	const price = parseFloat(booking.draft.price) || 0;
	return price + taxAmount.value;
});

// Computed properties for display
const formattedDate = computed(() => {
	if (!booking.draft.date) return "Not selected";
	const date = new Date(booking.draft.date);
	return date.toLocaleDateString("en-US", {
		weekday: "long",
		year: "numeric",
		month: "short",
		day: "numeric",
	});
});

const formattedTime = computed(() => {
	if (!booking.draft.slot?.start_time || !booking.draft.slot?.end_time) return "Not selected";
	return `${formatTime(booking.draft.slot.start_time)} — ${formatTime(
		booking.draft.slot.end_time
	)}`;
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
	return `${diffMins} Minutes Session`;
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
