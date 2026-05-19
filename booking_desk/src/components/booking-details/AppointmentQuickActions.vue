<template>
	<div class="flex flex-wrap gap-2">
		<button
			type="button"
			class="rounded-xl bg-primary text-on-primary px-4 py-2.5 text-[12px] font-semibold transition-all hover:opacity-90"
			@click="$emit('open')"
		>
			Open Appointment
		</button>
		<button
			type="button"
			class="rounded-xl border border-outline-variant px-4 py-2.5 text-[12px] font-semibold text-on-surface-variant transition-colors hover:bg-surface-container"
			@click="$emit('reschedule')"
		>
			Reschedule
		</button>
		<button
			type="button"
			class="rounded-xl border border-error/20 text-error px-4 py-2.5 text-[12px] font-semibold transition-colors hover:bg-error-container/20"
			@click="$emit('cancel')"
		>
			Cancel
		</button>
	</div>
</template>

<script setup>
defineEmits(["open", "reschedule", "cancel"]);
</script>
