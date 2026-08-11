<template>
	<div class="rounded-xl border border-outline-variant bg-surface p-4 space-y-3">
		<p class="text-[13px] font-semibold text-on-surface">Online Checkout Link</p>
		<p class="text-[11px] text-on-surface-variant">
			Generate a hosted payment link and share with the customer.
		</p>
		<div
			v-if="paymentUrl"
			class="rounded-lg bg-surface-container px-3 py-2 text-[12px] break-all"
		>
			{{ paymentUrl }}
		</div>
		<div class="flex gap-2" v-if="paymentUrl">
			<button
				type="button"
				class="rounded-lg border border-outline px-3 py-2 text-[12px]"
				@click="$emit('copyLink')"
			>
				Copy Link
			</button>
			<a
				:href="paymentUrl"
				target="_blank"
				rel="noreferrer"
				class="rounded-lg border border-secondary/40 px-3 py-2 text-[12px] font-semibold text-secondary-ink decoration-secondary underline-offset-4 transition-colors hover:bg-secondary-container hover:underline focus-visible:ring-2 focus-visible:ring-secondary"
			>
				Open Link
			</a>
		</div>
	</div>
</template>

<script setup>
defineProps({
	paymentUrl: {
		type: String,
		default: "",
	},
});

defineEmits(["copyLink"]);
</script>
