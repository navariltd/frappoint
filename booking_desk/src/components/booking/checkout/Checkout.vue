<template>
	<div class="h-full flex flex-col">
		<CheckoutLoadingState v-if="isLoading" />

		<div
			v-else-if="isRedirectingToBooking"
			class="h-full flex items-center justify-center bg-surface-container-lowest px-4"
		>
			<div class="w-full max-w-sm text-center space-y-3">
				<span
					class="material-symbols-outlined inline-flex text-[32px] text-primary animate-spin"
				>
					progress_activity
				</span>
				<div class="space-y-1">
					<h1 class="text-[18px] font-semibold text-on-surface">
						Redirecting to booking
					</h1>
					<p class="text-[13px] text-on-surface-variant">
						Payment confirmed. Opening {{ redirectingBookingId || "booking" }}...
					</p>
				</div>
			</div>
		</div>

		<template v-else>
			<header class="px-4 py-4 border-b border-outline-variant bg-surface-container-lowest">
				<div class="flex items-center gap-2 text-on-surface-variant mb-1">
					<span class="text-[11px] uppercase tracking-wider text-primary font-semibold">
						Booking Builder
					</span>
					<span class="material-symbols-outlined text-sm">chevron_right</span>
					<span class="text-[11px]">Step 3 of 3</span>
				</div>
				<h1 class="text-[20px] font-semibold text-on-surface">{{ checkoutTitle }}</h1>
				<p class="text-[13px] text-on-surface-variant">
					{{ checkoutSubtitle }}
				</p>
			</header>

			<div class="flex-1 min-h-0 flex overflow-hidden">
				<!-- LEFT SIDEBAR: Booking Summary -->
				<aside
					class="hidden md:flex flex-col w-72 lg:w-80 border-r border-outline-variant bg-surface-container-low p-4 overflow-y-auto gap-4 flex-shrink-0"
				>
					<div class="space-y-1 border-b border-outline-variant pb-3">
						<h2 class="text-[14px] font-semibold text-on-surface">Booking Summary</h2>
						<div class="space-y-1 text-[12px] text-on-surface-variant">
							<div class="flex items-center justify-between gap-2">
								<span>Booking ID</span>
								<span class="font-semibold text-on-surface">{{
									booking.name || "-"
								}}</span>
							</div>
							<div class="flex items-center justify-between gap-2">
								<span>Guests</span>
								<span class="font-semibold text-on-surface">{{ guestCount }}</span>
							</div>
							<div class="flex items-center justify-between gap-2">
								<span>Services</span>
								<span class="font-semibold text-on-surface">{{
									serviceCount
								}}</span>
							</div>
							<div class="flex items-center justify-between gap-2">
								<span>Status</span>
								<span class="font-semibold text-on-surface">{{
									booking.status || "Draft"
								}}</span>
							</div>
						</div>
					</div>

					<div class="space-y-2 flex-1 overflow-y-auto pr-1">
						<div
							v-if="!appointments.length"
							class="text-[12px] text-on-surface-variant px-1"
						>
							No appointments found.
						</div>
						<div
							v-for="appointment in appointments"
							:key="appointment.name || appointment.fullName"
							class="rounded-lg border border-outline-variant bg-surface-container-lowest p-2"
						>
							<div class="flex items-center justify-between gap-2">
								<p class="text-[12px] font-semibold">
									{{ appointment.fullName || "Guest" }}
								</p>
								<span
									class="rounded-full px-2 py-1 text-[10px] font-semibold"
									:class="
										appointment.paymentStatus === 'Paid'
											? 'bg-tertiary-container text-on-tertiary-container'
											: 'bg-secondary-container text-on-secondary-container'
									"
								>
									{{ appointment.paymentStatus || "Unpaid" }}
								</span>
							</div>
							<p class="text-[11px] text-on-surface-variant">
								{{ appointment.serviceType }}
							</p>
							<p class="text-[11px] text-on-surface-variant">
								<template v-if="appointment.date">{{ appointment.date }}</template>
								<template v-if="appointment.startTime">
									· {{ appointment.startTime }} –
									{{ appointment.endTime }}</template
								>
								<template v-if="appointment.provider">
									· {{ appointment.provider }}</template
								>
							</p>
							<p class="text-[11px] font-semibold text-primary mt-1">
								{{ formatCurrency(appointment.totalAmount || 0) }}
							</p>
						</div>
					</div>

					<div
						class="text-[11px] text-on-surface-variant border-t border-outline-variant pt-3"
					>
						{{ booking.fullName || "Walk-in Customer" }}
					</div>
				</aside>

				<!-- CENTER: Payment Workspace -->
				<section class="flex-1 min-w-0 p-4 overflow-y-auto space-y-4">
					<CheckoutValidationBanner :issues="combinedIssues" />
					<PaymentStatusBanner :message="statusMessage" :progress="paymentProgress" />

					<section
						v-if="canConfirmWithoutPayment"
						class="rounded-xl border border-primary bg-primary/10 p-4 flex items-start gap-3"
					>
						<span class="material-symbols-outlined text-[22px] text-primary">
							verified
						</span>
						<div class="space-y-1">
							<h3 class="text-[14px] font-semibold text-on-surface">
								Payment bypass enabled
							</h3>
							<p class="text-[12px] text-on-surface-variant">
								This booking can be confirmed now. The outstanding balance will
								remain available for later settlement.
							</p>
						</div>
					</section>

					<PaymentTypeSelector
						v-if="!canConfirmWithoutPayment"
						:paymentType="selectedPaymentType"
						:depositAmount="depositAmount"
						:minimumDue="financialSummary.minimumDue"
						:currency="currency"
						@update:paymentType="setPaymentType"
						@update:depositAmount="setDepositAmount"
					/>

					<section
						v-if="!canConfirmWithoutPayment"
						class="rounded-xl border border-outline-variant bg-surface p-4"
					>
						<h3 class="text-[14px] font-semibold text-on-surface mb-3">
							Payment Channel
						</h3>
						<div class="inline-flex rounded-xl bg-surface-container p-1">
							<button
								type="button"
								class="px-4 py-2 rounded-lg text-[12px] font-semibold transition-colors"
								:class="
									selectedPaymentChannel === 'offline'
										? 'bg-primary-container text-on-primary-container shadow-sm'
										: 'text-on-surface-variant hover:text-on-surface'
								"
								@click="setPaymentChannel('offline')"
							>
								Offline Payment
							</button>
							<button
								type="button"
								class="px-4 py-2 rounded-lg text-[12px] font-semibold transition-colors"
								:class="
									selectedPaymentChannel === 'online'
										? 'bg-primary-container text-on-primary-container shadow-sm'
										: 'text-on-surface-variant hover:text-on-surface'
								"
								@click="setPaymentChannel('online')"
							>
								Online Payment
							</button>
						</div>
					</section>

					<PaymentMethodSelector
						v-if="!canConfirmWithoutPayment"
						:methods="activeMethods"
						:paymentChannel="selectedPaymentChannel"
						:payableAmount="payableAmount"
						:currency="currency"
						:selectedMethodId="selectedMethodId"
						@update:selectedMethodId="handleMethodSelection"
					/>

					<PaymentWorkflowPanel
						v-if="!canConfirmWithoutPayment"
						:selectedMethod="selectedMethod"
						:manualAmountTendered="manualAmountTendered"
						:manualReferenceNo="manualReferenceNo"
						:payableAmount="payableAmount"
						:currency="currency"
						:mpesaPhone="mpesaPhone"
						:paymentUrl="hostedPaymentUrl"
						@update:manualAmountTendered="setManualAmountTendered"
						@update:manualReferenceNo="setManualReferenceNo"
						@update:mpesaPhone="setMpesaPhone"
						@copyLink="copyPaymentLink"
					/>
				</section>

				<!-- RIGHT SIDEBAR: Settlement Summary -->
				<PaymentSummarySidebar
					:currency="currency"
					:totalAmount="financialSummary.totalAmount"
					:paidAmount="financialSummary.paidAmount"
					:outstandingAmount="financialSummary.outstandingAmount"
					:payableAmount="payableAmount"
					:remainingAfterPayment="financialSummary.remainingAfterPayment"
					:submitLabel="submitLabel"
					:canSubmit="canSubmit"
					:isSubmitting="isSubmitting"
					:paymentProgress="paymentProgress"
					:bookingRef="booking.name"
					@submit="submitCheckoutPayment"
					@refresh="refreshSummary"
				/>
			</div>
		</template>
	</div>
</template>
<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import CheckoutLoadingState from "@/components/booking/checkout/CheckoutLoadingState.vue";
import CheckoutValidationBanner from "@/components/booking/checkout/CheckoutValidationBanner.vue";
import PaymentStatusBanner from "@/components/booking/checkout/PaymentStatusBanner.vue";
import PaymentTypeSelector from "@/components/booking/checkout/PaymentTypeSelector.vue";
import PaymentMethodSelector from "@/components/booking/checkout/PaymentMethodSelector.vue";
import PaymentWorkflowPanel from "@/components/booking/checkout/PaymentWorkflowPanel.vue";
import PaymentSummarySidebar from "@/components/booking/checkout/PaymentSummarySidebar.vue";
import { useCheckout } from "@/composables/booking/checkout/useCheckout";
import { usePaymentWorkflow } from "@/composables/booking/checkout/usePaymentWorkflow";
import { useMpesaPayment } from "@/composables/booking/checkout/useMpesaPayment";
import { useBookingWorkflowStore } from "@/stores/bookingWorkflow.store";
import { useServicesStore } from "@/stores/services.store";

const route = useRoute();
const router = useRouter();
const routeBookingId = String(route.query.booking_id || "");
const bookingWorkflowStore = useBookingWorkflowStore();
const servicesStore = useServicesStore();
const hasCompletedCheckout = ref(false);
const isRedirectingToBooking = ref(false);
const redirectingBookingId = ref("");

const {
	summary,
	selectedPaymentChannel,
	offlineMethods,
	onlineMethods,
	activeMethods,
	selectedPaymentType,
	selectedMethodId,
	depositAmount,
	mpesaPhone,
	manualAmountTendered,
	manualReferenceNo,
	paymentProgress,
	statusMessage,
	hostedPaymentUrl,
	isLoading,
	isSubmitting,
	error,
	financialSummary,
	selectedMethod,
	canConfirmWithoutPayment,
	payableAmount,
	validationIssues,
	canSubmit,
	setPaymentType,
	setPaymentChannel,
	setSelectedMethod,
	setDepositAmount,
	setMpesaPhone,
	setManualAmountTendered,
	setManualReferenceNo,
	confirmWithoutPayment,
	refreshSummary,
} = useCheckout(routeBookingId);

const { submitPayment } = usePaymentWorkflow();
const { startPolling, stopPolling } = useMpesaPayment();

const booking = computed(() => summary.value.booking || {});
const appointments = computed(() => booking.value.appointments || []);
const currency = computed(
	() => financialSummary.value.currency || booking.value.currency || "KES"
);

const checkoutTitle = computed(() =>
	canConfirmWithoutPayment.value ? "Confirm Booking" : "Complete Payment"
);
const checkoutSubtitle = computed(() =>
	canConfirmWithoutPayment.value
		? "Confirm the booking without collecting payment now."
		: "Choose a payment channel and settle the booking."
);

const guestCount = computed(() => {
	const keys = new Set();
	appointments.value.forEach((appointment) => {
		const key =
			appointment.fullName || appointment.mobileNo || appointment.email || appointment.name;
		if (key) keys.add(key);
	});
	return keys.size;
});

const serviceCount = computed(() =>
	Number((booking.value.items || []).length || appointments.value.length)
);

watch(
	() => [
		isLoading.value,
		isSubmitting.value,
		booking.value.name,
		financialSummary.value.outstandingAmount,
		financialSummary.value.totalAmount,
	],
	async ([loading, submitting, bookingName, outstandingAmount, totalAmount]) => {
		if (hasCompletedCheckout.value || loading || submitting || !bookingName) {
			return;
		}
		if (Number(totalAmount || 0) > 0 && Number(outstandingAmount || 0) <= 0) {
			await completeBookingCheckout();
		}
	}
);

const combinedIssues = computed(() => {
	const issues = [...validationIssues.value];
	if (error.value) {
		issues.unshift(error.value);
	}
	if (canConfirmWithoutPayment.value) {
		return issues;
	}
	if (selectedPaymentChannel.value === "offline" && !offlineMethods.value.length) {
		issues.push("No offline modes of payment are configured.");
	}
	if (selectedPaymentChannel.value === "online" && !onlineMethods.value.length) {
		issues.push("No online gateways are configured for this booking.");
	}
	return issues;
});

const submitLabel = computed(() => {
	if (isSubmitting.value) {
		return "Processing...";
	}

	if (canConfirmWithoutPayment.value) {
		return "Confirm Without Payment";
	}

	if (selectedPaymentChannel.value === "offline") {
		return "Complete Payment";
	}

	if (selectedPaymentChannel.value !== "online") {
		return "Select Payment Channel";
	}

	if (selectedMethod.value?.providerType === "mpesa") {
		return "Trigger Mpesa Push";
	}

	const capabilities = selectedMethod.value?.capabilities || [];
	if (capabilities.includes("link")) {
		return "Send Payment Link";
	}

	return "Generate Checkout Session";
});

function handleMethodSelection(methodId) {
	setSelectedMethod(methodId);
	if (selectedPaymentChannel.value === "offline") {
		setManualAmountTendered(payableAmount.value);
	}
}

function formatCurrency(amount) {
	const value = Number(amount || 0);
	return `${currency.value} ${value.toFixed(2)}`;
}

async function copyPaymentLink() {
	if (!hostedPaymentUrl.value) {
		return;
	}

	try {
		await navigator.clipboard.writeText(hostedPaymentUrl.value);
		statusMessage.value = "Payment link copied.";
	} catch {
		statusMessage.value = "Could not copy payment link.";
	}
}

async function submitCheckoutPayment() {
	if (!canSubmit.value) {
		return;
	}

	try {
		if (canConfirmWithoutPayment.value) {
			await confirmWithoutPayment();
			await completeBookingCheckout();
			return;
		}

		await submitPayment({ redirectTo: window.location.href });
		if (selectedMethod.value?.providerType === "mpesa") {
			startPolling({ onConfirmed: completeBookingCheckout });
		} else {
			stopPolling();
			if (selectedPaymentChannel.value === "offline") {
				await refreshSummary();
				await completeBookingCheckout();
				return;
			}
		}
		await refreshSummary();
	} catch {
		stopPolling();
	}
}

async function completeBookingCheckout() {
	if (hasCompletedCheckout.value) {
		return;
	}
	const bookingId = booking.value.name || routeBookingId;
	if (!bookingId) {
		return;
	}
	hasCompletedCheckout.value = true;
	isRedirectingToBooking.value = true;
	redirectingBookingId.value = bookingId;

	servicesStore.clearCart();
	bookingWorkflowStore.clearWorkflow();
	await new Promise((resolve) => window.setTimeout(resolve, 350));

	await router.replace({
		name: "BookingDetails",
		params: { bookingId },
	});
}
</script>
