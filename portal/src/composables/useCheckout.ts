import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useCheckoutStore } from "@/stores/checkout.store";
import { formatCurrency } from "@/utils";

export function useCheckout() {
	const store = useCheckoutStore();

	const {
		bookingId,
		summary,
		gateways,
		selectedPaymentType,
		selectedGatewayId,
		depositAmount,
		mpesaPhone,
		paymentProgress,
		statusMessage,
		hostedPaymentUrl,
		isLoading,
		isSubmitting,
		error,
	} = storeToRefs(store);

	// Computed helpers from getters
	const booking = computed(() => store.booking);
	const payment = computed(() => store.payment);
	const selectedGateway = computed(() => store.selectedGateway);
	const payableAmount = computed(() => store.payableAmount);
	const remainingAfterPayment = computed(() => store.remainingAfterPayment);
	const isBookingPaid = computed(() => store.isBookingPaid);
	const isMpesaGateway = computed(() => store.isMpesaGateway);
	const depositPercent = computed(() => store.depositPercent);
	const calculatedDepositAmount = computed(() => store.calculatedDepositAmount);
	const canSubmit = computed(() => store.canSubmit);
	const currency = computed(() => store.currency);

	// Formatted financial summary
	const financialSummary = computed(() => {
		const curr = currency.value;
		const p = payment.value;
		return {
			currency: curr,
			totalAmount: Number(p.totalAmount || 0),
			paidAmount: Number(p.paidAmount || 0),
			outstandingAmount: Number(p.outstandingAmount || 0),
			minimumDue: Number(p.minimumDue || 0),
			payableAmount: payableAmount.value,
			remainingAfterPayment: remainingAfterPayment.value,
			formattedTotal: formatCurrency(Number(p.totalAmount || 0), curr),
			formattedOutstanding: formatCurrency(Number(p.outstandingAmount || 0), curr),
			formattedPayable: formatCurrency(payableAmount.value, curr),
			formattedRemaining: formatCurrency(remainingAfterPayment.value, curr),
		};
	});

	// CTA button label based on selected gateway
	const payButtonLabel = computed(() => {
		if (isSubmitting.value) return "Processing...";
		if (isMpesaGateway.value) return "Send M-Pesa Push";
		return "Continue to Payment";
	});

	// Actions
	async function initializeCheckout(id: string) {
		await store.initializeCheckout(id);
	}

	function selectPaymentType(type: "full" | "deposit") {
		store.selectPaymentOption(type);
	}

	function selectGateway(gatewayId: string) {
		store.selectGateway(gatewayId);
	}

	function updateMpesaPhone(phone: string) {
		store.setMpesaPhone(phone);
	}

	function updateDepositAmount(amount: number) {
		store.setDepositAmount(amount);
	}

	async function submitPayment() {
		return store.initializePayment();
	}

	return {
		// State refs
		bookingId,
		gateways,
		selectedPaymentType,
		selectedGatewayId,
		depositAmount,
		mpesaPhone,
		paymentProgress,
		statusMessage,
		hostedPaymentUrl,
		isLoading,
		isSubmitting,
		error,
		// Computed
		booking,
		payment,
		selectedGateway,
		payableAmount,
		remainingAfterPayment,
		isBookingPaid,
		isMpesaGateway,
		depositPercent,
		calculatedDepositAmount,
		canSubmit,
		currency,
		financialSummary,
		payButtonLabel,
		// Actions
		initializeCheckout,
		selectPaymentType,
		selectGateway,
		updateMpesaPhone,
		updateDepositAmount,
		submitPayment,
		refreshSummary: store.refreshSummary,
		clearCheckout: store.clearCheckout,
		fetchPaymentGateways: store.fetchPaymentGateways,
		handlePaymentRedirect: store.handlePaymentRedirect,
	};
}
