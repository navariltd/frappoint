<template>
	<button
		class="text-label-sm font-semibold text-error hover:underline disabled:opacity-50"
		:disabled="loading"
		type="button"
		@click="$emit('remove')"
	>
		{{ loading ? "Removing..." : "Remove coupon" }}
	</button>
</template>

<script setup lang="ts">
defineProps<{
	loading?: boolean;
}>();

defineEmits<{
	remove: [];
}>();
</script>
