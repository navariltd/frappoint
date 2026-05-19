<template>
	<div v-if="message" class="rounded-xl border px-3 py-2 text-[12px]" :class="bannerClass">
		{{ message }}
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	message: {
		type: String,
		default: "",
	},
	progress: {
		type: String,
		default: "idle",
	},
});

const bannerClass = computed(() => {
	if (props.progress === "failed" || props.progress === "timeout") {
		return "border-error bg-error-container/30 text-error";
	}
	if (props.progress === "success") {
		return "border-secondary bg-secondary-container/30 text-secondary";
	}
	if (props.progress === "awaiting_confirmation" || props.progress === "processing") {
		return "border-primary bg-primary/10 text-primary";
	}
	return "border-outline-variant bg-surface-container-low text-on-surface-variant";
});
</script>
