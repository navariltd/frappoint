<template>
	<span
		class="px-2.5 py-1 rounded-md text-[10px] font-semibold uppercase tracking-[0.08em]"
		:class="badgeClass"
		>{{ status }}</span
	>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({ status: { type: String, default: "Unpaid" } });

const badgeClass = computed(() => {
	const status = String(props.status || "").toLowerCase();
	if (status === "paid") return "bg-secondary-container text-on-secondary-container";
	if (status === "partly paid") return "bg-tertiary-container text-on-tertiary-container";
	return "bg-error-container text-on-error-container";
});
</script>
