<template>
	<div class="flex flex-col h-full w-full">
		<div class="flex flex-col lg:flex-row gap-6 lg:gap-8 w-full p-6 md:p-8 flex-1">
			<!-- Left Column - Payment Form -->
			<div class="w-full lg:flex-1">
				<div class="mb-8">
					<label
						class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2"
						for="coupon-code"
					>
						Coupon Code
					</label>
					<input
						id="coupon-code"
						v-model="booking.draft.couponCode"
						type="text"
						placeholder="Enter coupon code"
						class="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all"
					/>
					<p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
						The discount will be validated when you submit the booking.
					</p>
				</div>

				<h2 class="text-xl font-bold text-gray-900 dark:text-white mb-6">
					Payment Method
				</h2>

				<PaymentGatewayList
					class="mb-8"
					:gateways="paymentGateways"
					v-model="selectedPaymentGateway"
				/>

				<ErrorMessage v-if="paymentError" :message="paymentError" class="mb-6" />
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
						<div>
							<h3 class="font-bold text-gray-900 dark:text-white text-lg mb-1">
								{{ summaryTitle }}
							</h3>
							<p class="text-sm text-gray-500 dark:text-gray-400">
								{{ summarySubtitle }}
							</p>
						</div>

						<div class="space-y-3 max-h-72 overflow-auto pr-1">
							<div
								v-for="(item, index) in appointmentItems"
								:key="`${item.appointment_type}-${index}`"
								class="rounded-xl border border-gray-200 dark:border-gray-700 p-4 bg-gray-50/70 dark:bg-gray-900/40"
							>
								<div class="flex items-start justify-between gap-3">
									<div>
										<p class="font-semibold text-gray-900 dark:text-white">
											{{ item.appointment_type || "Service" }}
										</p>
										<p class="text-sm text-gray-500 dark:text-gray-400">
											{{
												item.guest_full_name ||
												item.full_name ||
												item.fullName ||
												"Guest"
											}}
										</p>
										<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
											{{ item.date }} • {{ formatSlotLabel(item.slot) }}
										</p>
									</div>
									<div class="text-right">
										<p
											class="text-sm font-semibold text-gray-900 dark:text-white"
										>
											{{
												formatCurrency(
													item.price,
													item.currency || booking.draft.currency
												)
											}}
										</p>
									</div>
								</div>
							</div>
						</div>

						<div class="space-y-2.5 pt-2">
							<div class="flex justify-between text-sm">
								<span class="text-gray-600 dark:text-gray-400">Subtotal</span>
								<span class="font-medium text-gray-900 dark:text-white">
									{{ formatCurrency(subtotalAmount, booking.draft.currency) }}
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
							<span class="text-2xl font-bold text-primary">
								{{ formatCurrency(totalAmount, booking.draft.currency) }}
							</span>
						</div>
					</div>

					<!-- Security Message -->
					<div class="pt-4">
						<p class="text-xs text-center text-primary font-medium">
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
				class="px-8 py-3 rounded-xl bg-primary hover:bg-primary-dark hover:scale-105 text-on-primary font-bold shadow-lg transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
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
import { ErrorMessage } from "frappe-ui";
import { useBookingStore } from "@/stores/bookingStore";
import { formatCurrency } from "@/utils";
import { computed, ref } from "vue";
import PaymentGatewayList from "../PaymentGatewayList.vue";

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

const appointmentItems = computed(() => {
	if (booking.draft.appointments?.length) {
		return booking.draft.appointments;
	}

	if (
		booking.draft.serviceType &&
		booking.draft.date &&
		booking.draft.slot &&
		booking.draft.price
	) {
		return [booking.createAppointmentSnapshot()];
	}

	return [];
});

const subtotalAmount = computed(() =>
	appointmentItems.value.reduce((total, item) => total + (Number(item.price) || 0), 0)
);

const paymentError = computed(() => {
	if (!paymentGateways.value.length) {
		return "No payment methods are configured for this service.";
	}
	return "";
});

const platformFee = ref(0.0);
const taxRate = ref(0);

const taxAmount = computed(() => {
	return (subtotalAmount.value * taxRate.value) / 100;
});

const totalAmount = computed(() => {
	return subtotalAmount.value + platformFee.value + taxAmount.value;
});

const summaryTitle = computed(() => {
	if (appointmentItems.value.length <= 1) {
		return booking.draft.serviceType || "Service";
	}
	return `Booking with ${appointmentItems.value.length} appointments`;
});

const summarySubtitle = computed(() => {
	if (!appointmentItems.value.length) {
		return "No appointment selected";
	}

	const first = appointmentItems.value[0];
	return `${first.date || "Date not selected"} • ${formatSlotLabel(first.slot)}`;
});

function formatSlotLabel(slot) {
	if (!slot?.start_time || !slot?.end_time) return "Time not selected";
	return `${slot.start_time} - ${slot.end_time}`;
}
</script>
