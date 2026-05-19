<template>
	<section class="rounded-xl border border-outline-variant bg-surface p-4 space-y-3">
		<h3 class="text-[14px] font-semibold text-on-surface">Payment Workflow</h3>
		<CashPaymentSection
			v-if="
				selectedMethod?.providerType === 'cash' ||
				selectedMethod?.providerType === 'manual'
			"
			:amountTendered="manualAmountTendered"
			:referenceNo="manualReferenceNo"
			:payableAmount="payableAmount"
			:currency="currency"
			@update:amountTendered="$emit('update:manualAmountTendered', $event)"
			@update:referenceNo="$emit('update:manualReferenceNo', $event)"
		/>
		<MpesaPaymentSection
			v-else-if="selectedMethod?.providerType === 'mpesa'"
			:phoneNumber="mpesaPhone"
			@update:phoneNumber="$emit('update:mpesaPhone', $event)"
		/>
		<OnlineCheckoutSection v-else :paymentUrl="paymentUrl" @copyLink="$emit('copyLink')" />
	</section>
</template>

<script setup>
import CashPaymentSection from "@/components/booking/checkout/CashPaymentSection.vue";
import MpesaPaymentSection from "@/components/booking/checkout/MpesaPaymentSection.vue";
import OnlineCheckoutSection from "@/components/booking/checkout/OnlineCheckoutSection.vue";

defineProps({
	selectedMethod: {
		type: Object,
		default: null,
	},
	manualAmountTendered: {
		type: Number,
		default: 0,
	},
	manualReferenceNo: {
		type: String,
		default: "",
	},
	payableAmount: {
		type: Number,
		default: 0,
	},
	currency: {
		type: String,
		default: "KES",
	},
	mpesaPhone: {
		type: String,
		default: "",
	},
	paymentUrl: {
		type: String,
		default: "",
	},
});

defineEmits([
	"update:manualAmountTendered",
	"update:manualReferenceNo",
	"update:mpesaPhone",
	"copyLink",
]);
</script>
