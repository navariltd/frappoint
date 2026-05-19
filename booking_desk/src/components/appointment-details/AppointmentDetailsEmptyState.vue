<template>
	<div
		class="rounded-2xl border border-dashed border-outline-variant bg-surface-container-low p-8 text-center space-y-4"
	>
		<div
			class="mx-auto h-12 w-12 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center"
		>
			<span class="material-symbols-outlined">event_busy</span>
		</div>
		<div>
			<h3 class="text-lg font-semibold text-on-surface">Appointment unavailable</h3>
			<p class="text-sm text-on-surface-variant max-w-md mx-auto">
				{{ message || "We could not load the appointment record." }}
			</p>
		</div>
		<button
			class="px-4 py-2 rounded-full bg-primary text-on-primary font-medium"
			type="button"
			@click="$emit('retry')"
		>
			Retry
		</button>
	</div>
</template>

<script setup>
defineProps({
	message: { type: String, default: "" },
});

defineEmits(["retry"]);
</script>
