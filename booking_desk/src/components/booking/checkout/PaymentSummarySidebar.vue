<template>
	<aside
		class="w-full md:w-80 lg:w-96 bg-surface-container-low border-l border-outline-variant p-4 flex flex-col gap-4"
	>
		<div class="space-y-1 border-b border-outline-variant pb-3">
			<h2 class="text-[14px] font-semibold text-on-surface">Settlement Summary</h2>
			<p class="text-[12px] text-on-surface-variant">Review charges before processing.</p>
		</div>

		<div class="flex-1 overflow-y-auto space-y-2 pr-1">
			<OutstandingBalanceCard
				:currency="currency"
				:totalAmount="totalAmount"
				:paidAmount="paidAmount"
				:outstandingAmount="outstandingAmount"
				:payableAmount="payableAmount"
				:remainingAfterPayment="remainingAfterPayment"
			/>
			<div class="rounded-lg border px-3 py-2 flex items-center gap-2" :class="statusClass">
				<span class="material-symbols-outlined text-[18px]">{{ statusIcon }}</span>
				<div>
					<p class="text-[12px] font-semibold">{{ statusLabel }}</p>
					<p class="text-[11px] opacity-70 uppercase">{{ paymentProgress || "idle" }}</p>
				</div>
			</div>
		</div>

		<div class="space-y-3 border-t border-outline-variant pt-3">
			<button
				v-if="canConfirmWithoutPayment"
				type="button"
				class="w-full rounded-lg border border-primary px-4 py-3 text-[12px] font-semibold text-primary flex items-center justify-center gap-2 transition-colors"
				:class="
					canConfirmWithoutPaymentSubmit && !isSubmitting
						? 'hover:bg-primary/10'
						: 'opacity-60 cursor-not-allowed'
				"
				:disabled="!canConfirmWithoutPaymentSubmit || isSubmitting"
				@click="$emit('confirmWithoutPayment')"
			>
				<span class="material-symbols-outlined text-[18px]">verified</span>
				{{ isSubmitting ? "Processing..." : "Confirm Without Payment" }}
			</button>
			<button
				type="button"
				class="w-full rounded-lg px-4 py-3 text-[12px] font-semibold flex items-center justify-center gap-2 transition-colors"
				:class="
					canSubmit && !isSubmitting
						? 'bg-primary text-on-primary hover:bg-primary/90'
						: 'bg-primary/70 text-on-primary hover:bg-primary/80'
				"
				:disabled="isSubmitting"
				@click="$emit('submit')"
			>
				<span class="material-symbols-outlined text-[18px]">send_to_mobile</span>
				{{ isSubmitting ? "Processing..." : "Make Payment Now" }}
			</button>
			<button
				type="button"
				class="w-full rounded-lg border border-outline-variant px-4 py-2 text-[12px] font-semibold text-on-surface-variant flex items-center justify-center gap-2 hover:bg-surface-container transition-colors"
				:disabled="isSubmitting"
				@click="$emit('refresh')"
			>
				<span class="material-symbols-outlined text-[16px]">refresh</span>
				Refresh Summary
			</button>
			<p class="text-center text-[10px] text-on-surface-variant pt-1">
				Ref: {{ bookingRef || "—" }}
			</p>
		</div>
	</aside>
</template>

<script setup>
import { computed } from "vue";
import OutstandingBalanceCard from "@/components/booking/checkout/OutstandingBalanceCard.vue";

const props = defineProps({
	currency: { type: String, default: "KES" },
	totalAmount: { type: Number, default: 0 },
	paidAmount: { type: Number, default: 0 },
	outstandingAmount: { type: Number, default: 0 },
	payableAmount: { type: Number, default: 0 },
	remainingAfterPayment: { type: Number, default: 0 },
	submitLabel: { type: String, default: "Process Payment" },
	canSubmit: { type: Boolean, default: false },
	canConfirmWithoutPayment: { type: Boolean, default: false },
	canConfirmWithoutPaymentSubmit: { type: Boolean, default: false },
	isSubmitting: { type: Boolean, default: false },
	paymentProgress: { type: String, default: "idle" },
	bookingRef: { type: String, default: "" },
});

defineEmits(["submit", "confirmWithoutPayment", "refresh"]);

const statusClass = computed(() => {
	if (props.paymentProgress === "failed" || props.paymentProgress === "timeout") {
		return "border-error bg-error-container/30 text-error";
	}
	if (props.paymentProgress === "success") {
		return "border-secondary bg-secondary-container/30 text-secondary";
	}
	if (
		props.paymentProgress === "awaiting_confirmation" ||
		props.paymentProgress === "processing"
	) {
		return "border-primary bg-primary/10 text-primary";
	}
	return "border-outline-variant bg-surface text-on-surface-variant";
});

const statusIcon = computed(() => {
	if (props.paymentProgress === "failed" || props.paymentProgress === "timeout") return "error";
	if (props.paymentProgress === "success") return "check_circle";
	if (props.paymentProgress === "awaiting_confirmation") return "hourglass_empty";
	if (props.paymentProgress === "processing") return "sync";
	return "pending";
});

const statusLabel = computed(() => {
	if (props.paymentProgress === "success") return "Payment Confirmed";
	if (props.paymentProgress === "failed") return "Payment Failed";
	if (props.paymentProgress === "timeout") return "Payment Timed Out";
	if (props.paymentProgress === "awaiting_confirmation") return "Awaiting Confirmation";
	if (props.paymentProgress === "processing") return "Processing Payment";
	return "Awaiting Payment";
});
</script>
