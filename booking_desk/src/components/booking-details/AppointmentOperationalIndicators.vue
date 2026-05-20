<template>
	<div class="flex items-center gap-1.5 flex-wrap">
		<span
			class="px-2.5 py-1 rounded-md text-[10px] font-semibold uppercase tracking-[0.08em]"
			:class="statusClass"
			>{{ appointment.status }}</span
		>
		<span
			class="px-2.5 py-1 rounded-md text-[10px] font-semibold uppercase tracking-[0.08em]"
			:class="paymentClass"
			>{{ appointment.paymentStatus }}</span
		>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({ appointment: { type: Object, required: true } });

const statusClass = computed(() => {
	const status = String(props.appointment.status || "").toLowerCase();
	if (status === "checked in") return "bg-secondary-container text-on-secondary-container";
	if (status === "ongoing") return "bg-primary-container text-on-primary-container";
	if (status === "completed") return "bg-tertiary-container text-on-tertiary-container";
	if (status === "cancelled") return "bg-error-container text-on-error-container";
	return "bg-surface-container text-on-surface-variant";
});

const paymentClass = computed(() => {
	const status = String(props.appointment.paymentStatus || "").toLowerCase();
	if (status === "paid") return "bg-secondary-container text-on-secondary-container";
	if (status === "partly paid") return "bg-tertiary-container text-on-tertiary-container";
	return "bg-error-container text-on-error-container";
});
</script>
