<template>
	<div class="min-h-screen bg-surface-bright">
		<main class="w-full px-6 max-w-[1200px] mx-auto py-12">
			<div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
				<div>
					<nav class="flex items-center gap-2 mb-2">
						<router-link
							:to="{ name: 'Bookings' }"
							class="text-label-sm text-outline uppercase tracking-wider hover:text-primary transition-colors"
						>
							My Bookings
						</router-link>
						<span class="material-symbols-outlined text-[14px] text-outline"
							>chevron_right</span
						>
						<span class="text-label-sm text-primary font-bold uppercase tracking-wider"
							>Secure Checkout</span
						>
					</nav>
					<h1 class="font-headline-lg text-headline-lg text-on-surface mb-2">
						Complete Your Payment
					</h1>
					<p class="text-on-surface-variant font-body-md">
						Step 4 of 4 — Review your selection and complete your transaction securely.
					</p>
				</div>
				<div class="flex items-center gap-4 font-label-md text-label-md">
					<span class="text-on-surface-variant">Selection</span>
					<span class="material-symbols-outlined text-[16px] text-outline"
						>arrow_forward</span
					>
					<span class="text-on-surface-variant">Guests</span>
					<span class="material-symbols-outlined text-[16px] text-outline"
						>arrow_forward</span
					>
					<span class="text-on-surface-variant font-bold">Review</span>
					<span class="material-symbols-outlined text-[16px] text-outline"
						>arrow_forward</span
					>
					<span class="text-primary">Checkout</span>
				</div>
			</div>

			<div v-if="isLoading" class="flex items-center justify-center py-24">
				<div class="space-y-4 text-center">
					<div
						class="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto"
					></div>
					<p class="text-body-md text-on-surface-variant">Preparing checkout...</p>
				</div>
			</div>

			<div v-else-if="error && !booking.name" class="flex items-center justify-center py-24">
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

			<div
				v-else-if="booking.name"
				class="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start"
			>
				<div class="lg:col-span-7 flex flex-col gap-6">
					<div
						class="flex items-center gap-2 text-primary font-label-sm text-label-sm uppercase tracking-wide"
					>
						<span class="material-symbols-outlined text-[18px]">lock</span>
						Secure Checkout
					</div>

					<div
						class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-2 border-b border-outline-variant/30"
					>
						<div>
							<p
								class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-1"
							>
								Service Booking
							</p>
							<h2 class="font-headline-sm text-headline-sm text-on-surface">
								{{ booking.name }}
							</h2>
							<p class="font-body-md text-body-md text-on-surface-variant mt-1">
								{{ booking.fullName || booking.customer || "Guest" }}
								<template v-if="booking.email"
									>&middot; {{ booking.email }}</template
								>
							</p>
						</div>
						<div
							class="inline-flex items-center px-3 py-1 rounded-full bg-surface-container-high text-on-surface-variant font-label-sm text-label-sm"
						>
							<span
								class="w-2 h-2 rounded-full mr-2"
								:class="isBookingPaid ? 'bg-secondary' : 'bg-outline'"
							></span>
							{{ isBookingPaid ? "Paid" : "Payment Pending" }}
						</div>
					</div>

					<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
						<div
							class="bg-surface-bright border border-outline-variant/30 rounded-xl p-5 flex flex-col gap-2"
						>
							<span
								class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider"
								>Grand Total</span
							>
							<span
								class="font-headline-sm text-headline-sm text-on-surface font-bold"
								>{{ financialSummary.formattedFinal }}</span
							>
						</div>
						<div
							class="bg-surface-bright border border-outline-variant/30 rounded-xl p-5 flex flex-col gap-2"
						>
							<span
								class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider"
								>Outstanding</span
							>
							<span
								class="font-headline-sm text-headline-sm text-primary font-bold"
								>{{ financialSummary.formattedOutstanding }}</span
							>
						</div>
					</div>

					<div class="mt-4">
						<h3 class="font-headline-sm text-headline-sm text-on-surface mb-4">
							Your Appointments
						</h3>
						<p
							class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-3"
						>
							{{ booking.appointments.length }}
							{{
								booking.appointments.length === 1 ? "Appointment" : "Appointments"
							}}
						</p>
						<div class="space-y-4">
							<div
								v-for="appointment in booking.appointments"
								:key="appointment.name"
								class="bg-surface-bright border border-outline-variant/20 rounded-xl p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 hover:shadow-sm transition-shadow duration-300"
							>
								<div>
									<h4
										class="font-label-md text-label-md text-on-surface text-base mb-1"
									>
										{{ appointment.appointmentType || "Appointment" }}
									</h4>
									<p
										class="font-body-md text-body-md text-on-surface-variant text-sm mb-1"
									>
										{{ appointment.guestName || "Guest" }}
									</p>
									<div
										class="flex items-center gap-2 text-on-surface-variant font-label-sm text-label-sm"
									>
										<span class="material-symbols-outlined text-[16px]"
											>calendar_today</span
										>
										{{ formatDate(appointment.date) }}
										<template v-if="appointment.startTime">
											&middot; {{ formatTime(appointment.startTime) }}
											<template v-if="appointment.endTime">
												- {{ formatTime(appointment.endTime) }}
											</template>
										</template>
									</div>
								</div>
								<div
									class="flex flex-col items-end gap-1 text-right w-full sm:w-auto"
								>
									<span
										v-if="appointment.discountAmount > 0"
										class="font-body-md text-body-md text-on-surface-variant line-through text-sm"
									>
										{{ fmt(appointment.price || appointment.grandTotal) }}
									</span>
									<span
										class="font-label-md text-label-md text-on-surface text-base"
									>
										{{ fmt(appointment.grandTotal) }}
									</span>
									<span
										v-if="appointment.couponCode"
										class="font-label-sm text-label-sm text-primary"
									>
										Coupon: {{ appointment.couponCode }}
									</span>
									<span
										class="font-label-sm text-label-sm text-on-surface-variant mt-1"
									>
										{{ appointment.status || "Open" }}
									</span>
								</div>
							</div>
						</div>
					</div>

					<div class="grid grid-cols-3 gap-4 mt-6">
						<div
							class="bg-surface-bright border border-outline-variant/20 rounded-xl p-4 flex flex-col items-center justify-center text-center gap-2"
						>
							<span class="material-symbols-outlined text-primary"
								>verified_user</span
							>
							<span class="font-label-sm text-label-sm text-on-surface-variant"
								>SSL Encrypted</span
							>
						</div>
						<div
							class="bg-surface-bright border border-outline-variant/20 rounded-xl p-4 flex flex-col items-center justify-center text-center gap-2"
						>
							<span class="material-symbols-outlined text-primary"
								>event_available</span
							>
							<span class="font-label-sm text-label-sm text-on-surface-variant"
								>Instant Confirmation</span
							>
						</div>
						<div
							class="bg-surface-bright border border-outline-variant/20 rounded-xl p-4 flex flex-col items-center justify-center text-center gap-2"
						>
							<span class="material-symbols-outlined text-primary">restart_alt</span>
							<span class="font-label-sm text-label-sm text-on-surface-variant"
								>Flexible Refund</span
							>
						</div>
					</div>
				</div>

				<div class="lg:col-span-5 flex flex-col gap-6">
					<div
						class="bg-surface-container rounded-2xl p-6 sm:p-8 flex flex-col gap-6 shadow-sm"
					>
						<div>
							<h2
								class="font-headline-sm text-headline-sm text-on-surface mb-6 border-b border-outline-variant/20 pb-4"
							>
								Payment Details
							</h2>
							<p
								class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-2"
							>
								Amount Due Today
							</p>
							<div class="flex items-end justify-between gap-3">
								<span class="font-headline-lg text-headline-lg text-primary">{{
									financialSummary.formattedPayable
								}}</span>
								<span
									class="inline-flex items-center px-3 py-1 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-label-sm uppercase tracking-wider text-[10px]"
								>
									{{
										selectedPaymentType === "full" ? "Full Payment" : "Deposit"
									}}
								</span>
							</div>
						</div>

						<div>
							<p class="font-label-sm text-label-sm text-on-surface-variant mb-2">
								Payment Option
							</p>
							<div
								class="flex bg-surface-bright rounded-full p-1 border border-outline-variant/30"
							>
								<button
									class="flex-1 py-2 rounded-full font-label-md text-label-md text-sm transition-colors"
									:class="
										selectedPaymentType === 'full'
											? 'bg-primary text-on-primary shadow-sm'
											: 'text-on-surface-variant hover:text-on-surface'
									"
									@click="onSelectPaymentType('full')"
								>
									Pay Full Amount
								</button>
								<button
									:disabled="!depositEnabled"
									class="flex-1 py-2 rounded-full font-label-md text-label-md text-sm transition-colors"
									:class="
										selectedPaymentType === 'deposit'
											? 'bg-primary text-on-primary shadow-sm'
											: 'text-on-surface-variant hover:text-on-surface disabled:opacity-40 disabled:cursor-not-allowed'
									"
									@click="onSelectPaymentType('deposit')"
								>
									Pay Deposit
								</button>
							</div>
						</div>

						<div class="flex flex-col gap-3 py-4 border-y border-outline-variant/20">
							<div
								class="flex justify-between items-center font-body-md text-body-md text-on-surface-variant text-sm"
							>
								<span>Subtotal</span>
								<span>{{ financialSummary.formattedTotal }}</span>
							</div>
							<div
								class="flex justify-between items-center font-body-md text-body-md text-primary text-sm"
							>
								<span>Coupon savings</span>
								<span>-{{ fmt(totalSavings) }}</span>
							</div>
							<div
								class="flex justify-between items-center font-headline-sm text-headline-sm text-on-surface mt-2 pt-2"
							>
								<span>Total Due</span>
								<span class="text-primary font-bold">{{
									financialSummary.formattedPayable
								}}</span>
							</div>
							<div
								v-if="selectedPaymentType === 'deposit'"
								class="flex justify-between items-center font-body-md text-body-md text-on-surface-variant text-sm"
							>
								<span>Remaining after payment</span>
								<span>{{ financialSummary.formattedRemaining }}</span>
							</div>
						</div>

						<div>
							<p class="font-label-sm text-label-sm text-on-surface-variant mb-2">
								Payment Method
							</p>
							<div class="space-y-2">
								<button
									v-for="gateway in gateways"
									:key="gateway.id"
									type="button"
									class="w-full rounded-xl p-4 flex items-center justify-between cursor-pointer transition-colors border"
									:class="
										selectedGatewayId === gateway.id
											? 'bg-primary/5 border-primary hover:bg-primary/10'
											: 'bg-surface-bright border-outline-variant/30 hover:bg-surface-container-high/30'
									"
									@click="selectGateway(gateway.id)"
								>
									<div class="flex items-center gap-4 text-left">
										<div
											class="w-10 h-10 rounded-lg bg-primary text-on-primary flex items-center justify-center font-headline-sm font-bold"
										>
											{{
												(gateway.label || gateway.name || "G")
													.slice(0, 1)
													.toUpperCase()
											}}
										</div>
										<div>
											<p class="font-label-md text-label-md text-on-surface">
												{{ gateway.label || gateway.name }}
											</p>
											<p
												class="font-body-md text-body-md text-on-surface-variant text-xs"
											>
												{{ gateway.details || "Secure online payment" }}
											</p>
										</div>
									</div>
									<span
										class="material-symbols-outlined"
										:class="
											selectedGatewayId === gateway.id
												? 'text-primary'
												: 'text-outline'
										"
									>
										{{
											selectedGatewayId === gateway.id
												? "radio_button_checked"
												: "radio_button_unchecked"
										}}
									</span>
								</button>
							</div>
						</div>

						<div class="mt-2">
							<p
								v-if="isMpesaGateway"
								class="font-label-sm text-label-sm text-on-surface-variant mb-2"
							>
								Phone Number for M-Pesa
							</p>
							<input
								v-if="isMpesaGateway"
								:value="mpesaPhone"
								class="w-full bg-surface-bright border border-outline-variant rounded-lg font-body-md text-body-md px-4 py-3 mb-4 focus:border-primary focus:ring-1 focus:ring-primary transition-all text-on-surface"
								type="tel"
								placeholder="07XX XXX XXX"
								@input="
									updateMpesaPhone(($event.target as HTMLInputElement).value)
								"
							/>
							<button
								:disabled="!canSubmit"
								class="w-full py-4 bg-[#7BB4A7] text-white font-label-md text-label-md rounded-xl hover:bg-[#68a093] transition-colors shadow-sm mb-3 flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
								@click="handleSubmit"
							>
								{{ payButtonLabel }}
							</button>
							<div
								class="flex items-center justify-center gap-1.5 text-on-surface-variant font-label-sm text-label-sm text-xs"
							>
								<span class="material-symbols-outlined text-[14px]">lock</span>
								Secured with SSL encryption
							</div>
						</div>

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
					</div>

					<div class="px-2 mt-4">
						<h3
							class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-6"
						>
							Booking Progress
						</h3>
						<div class="relative flex flex-col gap-6 pl-3">
							<div
								class="absolute left-6 top-4 bottom-4 w-px bg-outline-variant/30"
							></div>
							<div class="flex gap-4 relative z-10">
								<div
									class="w-6 h-6 rounded-full bg-secondary text-on-secondary flex items-center justify-center flex-shrink-0 mt-0.5"
								>
									<span
										class="material-symbols-outlined text-[14px]"
										style="font-variation-settings: 'FILL' 1"
										>check</span
									>
								</div>
								<div>
									<p class="font-label-md text-label-md text-on-surface">
										Guests Assigned
									</p>
									<p
										class="font-body-md text-body-md text-on-surface-variant text-sm"
									>
										{{ booking.appointments.length }} appointment(s) scheduled
									</p>
								</div>
							</div>
							<div class="flex gap-4 relative z-10">
								<div
									class="w-6 h-6 rounded-full bg-primary text-on-primary flex items-center justify-center flex-shrink-0 mt-0.5 shadow-[0_0_0_4px_rgba(0,106,99,0.1)]"
								>
									<span
										class="material-symbols-outlined text-[14px]"
										style="font-variation-settings: 'FILL' 1"
										>credit_card</span
									>
								</div>
								<div>
									<p class="font-label-md text-label-md text-primary">Payment</p>
									<p
										class="font-body-md text-body-md text-on-surface-variant text-sm"
									>
										Completing your transaction
									</p>
								</div>
							</div>
							<div class="flex gap-4 relative z-10 opacity-50">
								<div
									class="w-6 h-6 rounded-full bg-surface-container-highest text-on-surface-variant flex items-center justify-center flex-shrink-0 mt-0.5 border border-outline-variant"
								>
									<span class="material-symbols-outlined text-[14px]"
										>check</span
									>
								</div>
								<div>
									<p class="font-label-md text-label-md text-on-surface">
										Confirmation
									</p>
									<p
										class="font-body-md text-body-md text-on-surface-variant text-sm"
									>
										Booking confirmation &amp; receipt
									</p>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</main>

		<PaymentProcessingOverlay :progress="paymentProgress" :message="statusMessage" />
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useCheckout } from "@/composables/useCheckout";
import { useCheckoutStore } from "@/stores/checkout.store";
import PaymentProcessingOverlay from "@/components/checkout/PaymentProcessingOverlay.vue";
import { formatCurrency } from "@/utils";

const route = useRoute();
const router = useRouter();
const store = useCheckoutStore();

const {
	gateways,
	selectedPaymentType,
	selectedGatewayId,
	couponDraft,
	couponMessage,
	couponError,
	isValidatingCoupon,
	isApplyingCoupon,
	mpesaPhone,
	paymentProgress,
	statusMessage,
	isLoading,
	isSubmitting,
	error,
	booking,
	isBookingPaid,
	payableAmount,
	remainingAfterPayment,
	isMpesaGateway,
	depositPercent,
	calculatedDepositAmount,
	canSubmit,
	currency,
	totalSavings,
	discountedTotal,
	appliedCoupon,
	financialSummary,
	payButtonLabel,
	initializeCheckout,
	selectPaymentType,
	selectGateway,
	setCouponDraft,
	applyCoupon,
	removeCoupon,
	updateMpesaPhone,
	submitPayment,
} = useCheckout();

const appliedCouponCode = computed(() => {
	if (!appliedCoupon.value) return "";
	if ("code" in appliedCoupon.value) {
		return appliedCoupon.value.code || appliedCoupon.value.name || "";
	}
	return appliedCoupon.value.coupon || "";
});

// Deposit is available only if minimumDue is less than total
const depositEnabled = computed(() => {
	const min = Number(store.summary.payment.minimumDue || 0);
	const total = Number(store.summary.payment.outstandingAmount || 0);
	return min > 0 && min < total;
});

function onSelectPaymentType(type: "full" | "deposit") {
	selectPaymentType(type);
}

function fmt(value: number) {
	return formatCurrency(Number(value || 0), currency.value);
}

function formatDate(value: string) {
	if (!value) return "Date pending";
	const date = new Date(`${value}T00:00:00`);
	if (Number.isNaN(date.getTime())) return value;
	return new Intl.DateTimeFormat("en-KE", {
		weekday: "short",
		day: "2-digit",
		month: "short",
		year: "numeric",
	}).format(date);
}

function formatTime(value: string) {
	if (!value) return "";
	const date = new Date(`1970-01-01T${value}`);
	if (Number.isNaN(date.getTime())) return value;
	return new Intl.DateTimeFormat("en-KE", {
		hour: "2-digit",
		minute: "2-digit",
		hour12: false,
	}).format(date);
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
