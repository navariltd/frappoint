<template>
	<div
		role="alert"
		class="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest px-4 py-3"
	>
		<div class="flex min-w-0 items-start gap-2.5">
			<span
				class="material-symbols-outlined mt-0.5 text-[20px] text-on-surface-variant"
				aria-hidden="true"
				>cloud_off</span
			>
			<div class="min-w-0">
				<p class="text-[13px] font-semibold text-on-surface">Couldn't load {{ what }}</p>
				<p v-if="reason" class="text-[12px] text-on-surface-variant">{{ reason }}</p>
			</div>
		</div>
		<button
			type="button"
			class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
			:disabled="busy"
			@click="emit('retry')"
		>
			{{ busy ? "Trying…" : "Try again" }}
		</button>
	</div>
</template>

<script setup>
// Shown in place of a list, count or empty state that failed to load, so nobody reads
// "0 arrivals" or "Nothing to review" when nothing was actually loaded.
defineProps({
	what: { type: String, required: true },
	reason: { type: String, default: "" },
	busy: { type: Boolean, default: false },
});
const emit = defineEmits(["retry"]);
</script>
