<template>
	<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase" :class="badgeClass">
		{{ statusLabel }}
	</span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	status: { type: String, default: "Open" },
});

const statusLabel = computed(() => String(props.status || "Open"));

const badgeClass = computed(() => {
	const normalized = statusLabel.value.toLowerCase();
	if (normalized === "in progress") {
		return "bg-secondary-container text-on-secondary-container";
	}
	if (normalized === "checked in") {
		return "bg-primary-container text-on-primary-container";
	}
	if (normalized === "completed") {
		return "bg-primary-container text-on-primary-container";
	}
	if (normalized === "rescheduled") {
		return "bg-error-container text-on-error-container";
	}
	if (normalized === "cancelled" || normalized === "closed") {
		return "bg-surface-variant text-on-surface-variant";
	}
	return "bg-surface-variant text-on-surface-variant";
});
</script>
