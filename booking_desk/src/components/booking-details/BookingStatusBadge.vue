<template>
	<span class="px-3 py-1 rounded-full text-[11px] font-semibold" :class="badgeClass">{{
		status
	}}</span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({ status: { type: String, default: "Draft" } });

const badgeClass = computed(() => {
	const status = String(props.status || "").toLowerCase();
	if (status === "confirmed" || status === "checked in")
		return "bg-secondary-container text-on-secondary-container";
	if (status === "completed") return "bg-tertiary-container text-on-tertiary-container";
	if (status === "cancelled") return "bg-error-container text-on-error-container";
	return "bg-surface-container text-on-surface-variant";
});
</script>
