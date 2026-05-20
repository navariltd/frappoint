<template>
	<div class="space-y-4">
		<BookingFinancialSummary :summary="financialSummary" :currency="currency" />
		<OperationalAlertsPanel :alerts="alerts" />
		<div class="space-y-2.5">
			<button
				class="w-full bg-primary text-on-primary px-4 py-2.5 rounded-md text-[12px] font-semibold flex items-center justify-center gap-2 transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-45 disabled:cursor-not-allowed"
				@click="$emit('collect-payment')"
			>
				<span class="material-symbols-outlined text-[18px]">credit_score</span>
				Collect Payment
			</button>
			<button
				class="w-full border border-primary text-primary px-4 py-2.5 rounded-md text-[12px] font-semibold flex items-center justify-center gap-2 transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
				@click="$emit('add-appointment')"
			>
				<span class="material-symbols-outlined text-[18px]">calendar_add_on</span>
				Add Appointment
			</button>
			<button
				class="w-full border border-outline-variant text-on-surface-variant px-4 py-2.5 rounded-md text-[12px] font-semibold flex items-center justify-center gap-2 hover:bg-surface-container-high transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
				@click="$emit('reschedule-booking')"
			>
				<span class="material-symbols-outlined text-[18px]">mail</span>
				Resend Confirmation
			</button>
		</div>
	</div>
</template>

<script setup>
import BookingFinancialSummary from "@/components/booking-details/BookingFinancialSummary.vue";
import OperationalAlertsPanel from "@/components/booking-details/OperationalAlertsPanel.vue";

defineProps({
	financialSummary: { type: Object, required: true },
	currency: { type: String, default: "KES" },
	alerts: { type: Array, default: () => [] },
});

defineEmits(["collect-payment", "add-appointment", "reschedule-booking"]);
</script>
