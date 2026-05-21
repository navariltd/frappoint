<template>
	<div class="min-h-screen bg-surface-bright flex flex-col">
		<!-- Header -->
		<header class="border-b border-outline-variant/20 px-6 py-4 bg-surface">
			<div class="max-w-7xl mx-auto flex items-center gap-2 text-on-surface-variant mb-1">
				<router-link
					:to="{ name: 'Bookings' }"
					class="text-label-sm hover:text-primary transition-colors"
				>
					My Bookings
				</router-link>
				<span class="material-symbols-outlined text-sm">chevron_right</span>
				<span class="text-label-sm uppercase tracking-wider font-semibold text-primary"
					>Secure Checkout</span
				>
			</div>
			<div class="max-w-7xl mx-auto">
				<h1 class="text-headline-lg font-headline-lg text-on-surface">
					Complete Your Payment
				</h1>
				<p class="text-body-md text-on-surface-variant">
					Review your selection and complete your transaction securely.
				</p>
			</div>
		</header>

		<!-- Loading State -->
		<div v-if="isLoading" class="flex-1 flex items-center justify-center">
			<div class="space-y-4 text-center">
				<div
					class="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto"
				></div>
				<p class="text-body-md text-on-surface-variant">Preparing checkout...</p>
			</div>
		</div>

		<!-- Error State -->
		<div
			v-else-if="error && !booking.name"
			class="flex-1 flex items-center justify-center p-8"
		>
			<div class="max-w-md text-center space-y-4">
				<div
					class="w-16 h-16 rounded-full bg-error-container/30 flex items-center justify-center mx-auto"
				>
					<span class="material-symbols-outlined text-error text-[32px]"
						>error_outline</span
					>
				</div>
				<p class="text-body-md text-on-surface">{{ error }}</p>
				<button
					class="px-6 py-2 rounded-full bg-primary text-on-primary font-semibold"
					@click="retry"
				>
					Retry
				</button>
			</div>
		</div>

		<!-- Main Checkout Layout -->
		<main v-else-if="booking.name" class="flex-1">
			<div class="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
				<!-- LEFT: Booking Summary -->
				<div class="lg:col-span-7 space-y-6">
					<div class="flex items-center gap-2 text-primary">
						<span class="material-symbols-outlined text-[18px]">lock</span>
						<span class="text-label-sm uppercase tracking-widest font-semibold"
							>Secure Checkout</span
						>
					</div>

					<BookingSummaryCard :booking="booking" />

					<div class="glass-card rounded-xl p-6 space-y-4">
						<h3 class="text-headline-sm font-headline-sm text-on-surface">
							Your Appointments
						</h3>
						<AppointmentSummaryList
							:appointments="booking.appointments"
							:currency="currency"
						/>
					</div>

					<!-- Trust Signals -->
					<div class="grid grid-cols-3 gap-3">
						<div
							class="flex flex-col items-center text-center p-4 rounded-xl border border-outline-variant/20"
						>
							<span class="material-symbols-outlined text-primary mb-1"
								>verified</span
							>
							<p class="text-label-sm text-on-surface-variant">SSL Encrypted</p>
						</div>
						<div
							class="flex flex-col items-center text-center p-4 rounded-xl border border-outline-variant/20"
						>
							<span class="material-symbols-outlined text-primary mb-1"
								>event_available</span
							>
							<p class="text-label-sm text-on-surface-variant">
								Instant Confirmation
							</p>
						</div>
						<div
							class="flex flex-col items-center text-center p-4 rounded-xl border border-outline-variant/20"
						>
							<span class="material-symbols-outlined text-primary mb-1">replay</span>
							<p class="text-label-sm text-on-surface-variant">Flexible Refund</p>
						</div>
					</div>
				</div>

				<!-- RIGHT: Payment Panel -->
				<div class="lg:col-span-5 space-y-5">
					<div
						class="bg-surface-container-highest rounded-xl border border-primary/10 shadow-lg p-6 space-y-6"
					>
						<h3 class="text-headline-sm font-headline-sm text-on-surface">
							Payment Details
						</h3>

						<!-- Amount header -->
						<div
							class="flex justify-between items-end pb-5 border-b border-outline-variant/20"
						>
							<div>
								<p
									class="text-label-sm text-on-surface-variant uppercase tracking-tighter mb-1"
								>
									Amount Due Today
								</p>
								<h2 class="text-headline-lg font-headline-lg text-primary">
									{{ financialSummary.formattedPayable }}
								</h2>
							</div>
							<span
								class="bg-secondary-container text-on-secondary-container px-3 py-1 rounded-lg text-label-sm font-bold uppercase"
							>
								{{ selectedPaymentType === "full" ? "Full Payment" : "Deposit" }}
							</span>
						</div>

						<!-- Payment type selection -->
						<div class="space-y-2">
							<p class="text-label-md font-semibold text-on-surface">
								Payment Option
							</p>
							<PaymentOptionSelector
								:selected="selectedPaymentType"
								:deposit-enabled="depositEnabled"
								@select="onSelectPaymentType"
							/>
						</div>

						<!-- Totals breakdown -->
						<CheckoutTotalsCard
							:booking="booking"
							:payable-amount="payableAmount"
							:deposit-amount="calculatedDepositAmount"
							:deposit-percent="depositPercent"
							:remaining-after-payment="remainingAfterPayment"
							:currency="currency"
							:payment-type="selectedPaymentType"
						/>

						<!-- Error message -->
						<div
							v-if="error"
							class="p-3 rounded-lg bg-error-container/20 border border-error/20"
						>
							<p
								class="text-body-sm text-on-error-container flex items-center gap-2"
							>
								<span class="material-symbols-outlined text-error text-[16px]"
									>warning</span
								>
								{{ error }}
							</p>
						</div>

						<!-- Gateway Selection -->
						<div class="space-y-3">
							<p class="text-label-md font-semibold text-on-surface">
								Payment Method
							</p>
							<PaymentGatewaySelector
								:gateways="gateways"
								:selected-id="selectedGatewayId"
								@select="selectGateway"
							/>
						</div>

						<!-- CTA Footer -->
						<CheckoutActionFooter
							:label="payButtonLabel"
							:can-submit="canSubmit"
							:submitting="isSubmitting"
							:is-mpesa="isMpesaGateway"
							:mpesa-phone="mpesaPhone"
							@submit="handleSubmit"
							@update-phone="updateMpesaPhone"
						/>
					</div>

					<!-- Booking Progress Indicator -->
					<div class="glass-card rounded-xl p-5">
						<h4
							class="text-label-md font-semibold text-on-surface mb-4 uppercase tracking-wider"
						>
							Booking Progress
						</h4>
						<div class="relative space-y-5">
							<div
								class="absolute left-[15px] top-2 bottom-2 w-0.5 bg-outline-variant/30"
							></div>

							<div class="flex items-start gap-4 relative z-10">
								<div
									class="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-on-secondary shadow-sm flex-shrink-0"
								>
									<span class="material-symbols-outlined text-[16px]"
										>check</span
									>
								</div>
								<div>
									<p class="text-label-md font-semibold text-on-surface">
										Guests Assigned
									</p>
									<p class="text-label-sm text-on-surface-variant">
										{{ booking.appointments.length }} appointment(s) scheduled
									</p>
								</div>
							</div>

							<div class="flex items-start gap-4 relative z-10">
								<div
									class="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary shadow-md ring-4 ring-primary-container/20 flex-shrink-0"
								>
									<span class="material-symbols-outlined text-[16px]"
										>payments</span
									>
								</div>
								<div>
									<p class="text-label-md font-bold text-primary">Payment</p>
									<p class="text-label-sm text-on-surface-variant">
										Completing your transaction
									</p>
								</div>
							</div>

							<div class="flex items-start gap-4 relative z-10">
								<div
									class="w-8 h-8 rounded-full bg-surface-container-high border-2 border-outline-variant/30 flex items-center justify-center text-on-surface-variant/40 flex-shrink-0"
								>
									<span class="material-symbols-outlined text-[16px]"
										>done_all</span
									>
								</div>
								<div>
									<p class="text-label-md text-on-surface-variant/60">
										Confirmation
									</p>
									<p class="text-label-sm text-on-surface-variant/40">
										Booking confirmation & receipt
									</p>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</main>

		<!-- Payment Processing Overlay -->
		<PaymentProcessingOverlay :progress="paymentProgress" :message="statusMessage" />
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useCheckout } from "@/composables/useCheckout";
import { useCheckoutStore } from "@/stores/checkout.store";
import BookingSummaryCard from "@/components/checkout/BookingSummaryCard.vue";
import AppointmentSummaryList from "@/components/checkout/AppointmentSummaryList.vue";
import PaymentOptionSelector from "@/components/checkout/PaymentOptionSelector.vue";
import PaymentGatewaySelector from "@/components/checkout/PaymentGatewaySelector.vue";
import CheckoutTotalsCard from "@/components/checkout/CheckoutTotalsCard.vue";
import CheckoutActionFooter from "@/components/checkout/CheckoutActionFooter.vue";
import PaymentProcessingOverlay from "@/components/checkout/PaymentProcessingOverlay.vue";

const route = useRoute();
const router = useRouter();
const store = useCheckoutStore();

const {
	bookingId,
	gateways,
	selectedPaymentType,
	selectedGatewayId,
	mpesaPhone,
	paymentProgress,
	statusMessage,
	isLoading,
	isSubmitting,
	error,
	booking,
	payableAmount,
	remainingAfterPayment,
	isMpesaGateway,
	depositPercent,
	calculatedDepositAmount,
	canSubmit,
	currency,
	financialSummary,
	payButtonLabel,
	initializeCheckout,
	selectPaymentType,
	selectGateway,
	updateMpesaPhone,
	submitPayment,
} = useCheckout();

// Deposit is available only if minimumDue is less than total
const depositEnabled = computed(() => {
	const min = Number(store.summary.payment.minimumDue || 0);
	const total = Number(store.summary.payment.outstandingAmount || 0);
	return min > 0 && min < total;
});

function onSelectPaymentType(type: "full" | "deposit") {
	selectPaymentType(type);
}

async function handleSubmit() {
	try {
		await submitPayment();
	} catch {
		// Error is managed by store
	}
}

async function retry() {
	const id = route.params.bookingId as string;
	if (id) await initializeCheckout(id);
}

onMounted(async () => {
	const id = route.params.bookingId as string;
	if (!id) {
		router.push({ name: "Bookings" });
		return;
	}
	await initializeCheckout(id);
});
</script>
