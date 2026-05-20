<template>
	<span
		class="px-2.5 py-1 rounded-md text-[10px] font-semibold uppercase tracking-[0.08em]"
		:class="badgeClass"
	>
		{{ label }}
	</span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	label: { type: String, default: "Open" },
	type: { type: String, default: "status" },
});

const badgeClass = computed(() => {
	const value = String(props.label || "")
		.trim()
		.toLowerCase();

	if (props.type === "event") {
		if (value.includes("payment")) return "bg-secondary-container text-on-secondary-container";
		if (value.includes("booking")) return "bg-primary-container text-on-primary-container";
		if (value.includes("check")) return "bg-secondary-fixed text-on-secondary-fixed-variant";
		if (value.includes("rescheduled"))
			return "bg-tertiary-container text-on-tertiary-container";
		if (value.includes("cancel")) return "bg-error-container text-on-error-container";
		return "bg-surface-container-high text-on-surface-variant";
	}

	if (props.type === "payment") {
		if (value === "paid") return "bg-secondary-container text-on-secondary-container";
		if (value === "partly paid") return "bg-tertiary-container text-on-tertiary-container";
		return "bg-error-container text-on-error-container";
	}

	if (["checked in", "checked-in"].includes(value)) {
		return "bg-secondary-fixed text-on-secondary-fixed-variant";
	}
	if (["ongoing", "in progress"].includes(value)) {
		return "bg-primary text-on-primary";
	}
	if (value === "completed") {
		return "bg-secondary-container text-on-secondary-container";
	}
	if (value === "cancelled") {
		return "bg-error-container text-on-error-container";
	}
	if (value === "pending payment") {
		return "bg-tertiary-container text-on-tertiary-container";
	}

	return "bg-surface-container-high text-on-surface-variant";
});
</script>
