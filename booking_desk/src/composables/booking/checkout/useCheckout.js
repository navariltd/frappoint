import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useCheckoutStore } from "@/stores/checkout.store";

export function useCheckout(bookingId = "") {
	const store = useCheckoutStore();
	const refs = storeToRefs(store);

	onMounted(() => {
		store.initializeCheckout(bookingId);
	});

	const financialSummary = computed(() => {
		const payment = refs.summary.value.payment || {};
		return {
			totalAmount: Number(payment.totalAmount || 0),
			paidAmount: Number(payment.paidAmount || 0),
			outstandingAmount: Number(payment.outstandingAmount || 0),
			minimumDue: Number(payment.minimumDue || 0),
			payableAmount: Number(store.payableAmount || 0),
			remainingAfterPayment: Number(store.remainingAfterPayment || 0),
			currency: payment.currency || "KES",
		};
	});

	return {
		...refs,
		financialSummary,
		activeMethods: computed(() => store.activeMethods),
		selectedMethod: computed(() => store.selectedMethod),
		payableAmount: computed(() => store.payableAmount),
		remainingAfterPayment: computed(() => store.remainingAfterPayment),
		validationIssues: computed(() => store.validationIssues),
		canSubmit: computed(() => store.canSubmit),
		setPaymentType: store.setPaymentType,
		setPaymentChannel: store.setPaymentChannel,
		setSelectedMethod: store.setSelectedMethod,
		setDepositAmount: store.setDepositAmount,
		setMpesaPhone: store.setMpesaPhone,
		setManualAmountTendered: store.setManualAmountTendered,
		setManualReferenceNo: store.setManualReferenceNo,
		refreshSummary: store.refreshSummary,
	};
}
