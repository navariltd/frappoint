<template>
	<div class="flex flex-col h-full">
		<div class="flex flex-col lg:flex-row gap-6 lg:gap-8 w-full p-6 md:p-8 flex-1">
			<!-- Left Column - Payment Form -->
			<div class="w-full lg:flex-1">
				<h2 class="text-xl font-bold text-gray-900 dark:text-white mb-6">
					Payment Method
				</h2>

				<div class="space-y-3 mb-8">
					<!-- M-Pesa Payment Option -->
					<label
						class="flex items-center gap-4 p-4 sm:p-5 border-2 rounded-xl sm:rounded-2xl cursor-pointer transition-all"
						:class="{
							'border-[#16a34a] bg-[#16a34a]/5':
								booking.draft.selectedPaymentGateway === 'Mpesa',
							'border-gray-200 hover:border-gray-300':
								booking.draft.selectedPaymentGateway !== 'Mpesa',
						}"
					>
						<div
							class="flex items-center justify-center w-12 h-12 sm:w-14 sm:h-14 bg-white rounded-xl border border-gray-200 flex-shrink-0"
						>
							<MpesaIcon />
						</div>
						<div class="flex-1 min-w-0">
							<h3
								class="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-0.5"
							>
								M-Pesa
							</h3>
							<p class="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
								Pay with your M-Pesa mobile money
							</p>
						</div>
						<div class="flex-shrink-0">
							<div
								class="w-5 h-5 sm:w-6 sm:h-6 rounded-full border-2 flex items-center justify-center transition-all"
								:class="{
									'border-[#16a34a] bg-[#16a34a]':
										booking.draft.selectedPaymentGateway === 'Mpesa',
									'border-gray-300':
										booking.draft.selectedPaymentGateway !== 'Mpesa',
								}"
							>
								<div
									v-if="booking.draft.selectedPaymentGateway === 'Mpesa'"
									class="w-2 h-2 sm:w-2.5 sm:h-2.5 bg-white rounded-full"
								></div>
							</div>
						</div>
						<input
							type="radio"
							name="payment_gateway"
							value="Mpesa"
							v-model="booking.draft.selectedPaymentGateway"
							class="sr-only"
						/>
					</label>

					<!-- PayPal Payment Option -->
					<label
						class="flex items-center gap-4 p-4 sm:p-5 border-2 rounded-xl sm:rounded-2xl cursor-pointer transition-all"
						:class="{
							'border-[#0070ba] bg-[#0070ba]/5':
								booking.draft.selectedPaymentGateway === 'Paypal',
							'border-gray-200 hover:border-gray-300':
								booking.draft.selectedPaymentGateway !== 'Paypal',
						}"
					>
						<div
							class="flex items-center justify-center w-12 h-12 sm:w-14 sm:h-14 bg-white rounded-xl border border-gray-200 flex-shrink-0"
						>
							<PaypalIcon />
						</div>
						<div class="flex-1 min-w-0">
							<h3
								class="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-0.5"
							>
								PayPal
							</h3>
							<p class="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
								Pay safely with your PayPal account
							</p>
						</div>
						<div class="flex-shrink-0">
							<div
								class="w-5 h-5 sm:w-6 sm:h-6 rounded-full border-2 flex items-center justify-center transition-all"
								:class="{
									'border-[#0070ba] bg-[#0070ba]':
										booking.draft.selectedPaymentGateway === 'Paypal',
									'border-gray-300':
										booking.draft.selectedPaymentGateway !== 'Paypal',
								}"
							>
								<div
									v-if="booking.draft.selectedPaymentGateway === 'Paypal'"
									class="w-2 h-2 sm:w-2.5 sm:h-2.5 bg-white rounded-full"
								></div>
							</div>
						</div>
						<input
							type="radio"
							name="payment_gateway"
							value="Paypal"
							v-model="booking.draft.selectedPaymentGateway"
							class="sr-only"
						/>
					</label>
				</div>
			</div>

			<!-- Right Column - Order Summary -->
			<aside class="w-full lg:w-80 xl:w-96 flex-shrink-0">
				<div
					class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 sticky top-24"
				>
					<h2 class="text-lg font-bold text-gray-900 dark:text-white mb-6">
						Order Summary
					</h2>

					<div class="space-y-4 pb-6 border-b border-gray-100 dark:border-gray-800">
						<!-- Service Info -->
						<div>
							<h3 class="font-bold text-gray-900 dark:text-white text-lg mb-1">
								{{ booking.draft.serviceType || "Service" }}
							</h3>
							<p class="text-sm text-gray-500 dark:text-gray-400">
								{{ formattedDate }} • {{ formattedTime }}
							</p>
						</div>

						<!-- Price Breakdown -->
						<div class="space-y-2.5 pt-2">
							<div class="flex justify-between text-sm">
								<span class="text-gray-600 dark:text-gray-400">Service Fee</span>
								<span class="font-medium text-gray-900 dark:text-white">
									{{
										formatCurrency(booking.draft.price, booking.draft.currency)
									}}
								</span>
							</div>
							<div class="flex justify-between text-sm">
								<span class="text-gray-600 dark:text-gray-400">Platform Fee</span>
								<span class="font-medium text-gray-900 dark:text-white">
									{{ formatCurrency(platformFee, booking.draft.currency) }}
								</span>
							</div>
							<div class="flex justify-between text-sm">
								<span class="text-gray-600 dark:text-gray-400"
									>Service Tax ({{ taxRate }}%)</span
								>
								<span class="font-medium text-gray-900 dark:text-white">
									{{ formatCurrency(taxAmount, booking.draft.currency) }}
								</span>
							</div>
						</div>
					</div>

					<!-- Grand Total -->
					<div class="py-6 border-b border-gray-100 dark:border-gray-800">
						<div class="flex justify-between items-baseline">
							<span class="text-lg font-bold text-gray-900 dark:text-white"
								>Grand Total</span
							>
							<span class="text-2xl font-bold text-[#16a34a]">
								{{ formatCurrency(totalAmount, booking.draft.currency) }}
							</span>
						</div>
					</div>

					<!-- Security Message -->
					<div class="pt-4">
						<p class="text-xs text-center text-[#16a34a] font-medium">
							Your data is safe. We use high-level encryption for all payment
							processes.
						</p>
					</div>
				</div>
			</aside>
		</div>

		<!-- Proceed Button -->
		<div
			class="px-6 md:px-8 pb-6 md:pb-8 flex items-center justify-between border-t border-gray-100 pt-6"
		>
			<button
				@click="emit('back')"
				class="px-6 py-3 rounded-xl border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-semibold hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				type="button"
			>
				Back
			</button>
			<button
				:disabled="!canProceed || !booking.draft.selectedPaymentGateway"
				@click="emit('submit')"
				class="px-8 py-3 rounded-xl bg-[#16a34a] hover:bg-[#15803d] text-white font-bold shadow-lg transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
				type="button"
			>
				Proceed to Pay
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M13 7l5 5m0 0l-5 5m5-5H6"
					/>
				</svg>
			</button>
		</div>
	</div>
</template>

<script setup>
import { useBookingStore } from "@/stores/bookingStore";
import { formatCurrency } from "@/utils";
import { computed, ref } from "vue";
import MpesaIcon from "../../icons/MpesaIcon.vue";
import PaypalIcon from "../../icons/PaypalIcon.vue";

const props = defineProps({
	canProceed: Boolean,
});

const emit = defineEmits(["back", "submit"]);

const booking = useBookingStore();

const paymentGateways = computed(() => booking.draft.paymentGateways);
const selectedPaymentGateway = computed({
	get: () => booking.draft.selectedPaymentGateway,
	set: (v) => booking.selectPaymentGateway(v),
});

// Fee calculations
const platformFee = ref(5.5);
const taxRate = ref(8);

const taxAmount = computed(() => {
	const price = parseFloat(booking.draft.price) || 0;
	return (price * taxRate.value) / 100;
});

const totalAmount = computed(() => {
	const price = parseFloat(booking.draft.price) || 0;
	return price + platformFee.value + taxAmount.value;
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
