<template>
	<span
		class="px-3 py-1 rounded-full text-[11px] font-semibold whitespace-nowrap"
		:class="badgeClass"
	>
		{{ status }}
	</span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({ status: { type: String, default: "" } });

const badgeClass = computed(() => {
	switch (props.status) {
		case "Held":
		case "Option":
		case "Settlement Pending":
		case "Queued":
		case "Running":
		case "Requested":
		case "Partly Paid":
		case "Post-Stay Open":
			return "bg-tertiary-container text-on-tertiary-container";
		case "Confirmed":
		case "Due In":
		case "In House":
		case "Open":
		case "Completed":
		case "Received":
		case "Applied":
		case "Active":
			return "bg-secondary-container text-on-secondary-container";
		case "Cancelled":
		case "No Show":
		case "Partly Cancelled":
		case "Failed":
		case "Forfeited":
		case "Released":
			return "bg-error-container text-on-error-container";
		default:
			return "bg-surface-container text-on-surface-variant";
	}
});
</script>
