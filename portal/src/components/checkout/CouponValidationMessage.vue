<template>
	<div v-if="message" class="rounded-xl p-3 text-body-sm" :class="messageClass">
		{{ message }}
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
	message: string;
	type?: "success" | "error" | "info";
}>();

const messageClass = computed(() => {
	if (props.type === "success") {
		return "bg-secondary-container/40 text-on-secondary-container border border-secondary/30";
	}
	if (props.type === "error") {
		return "bg-error-container/30 text-on-error-container border border-error/30";
	}
	return "bg-surface-container text-on-surface-variant border border-outline-variant/30";
});
</script>
