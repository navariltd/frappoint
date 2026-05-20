<template>
	<section
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
					Financial Summary
				</p>
			</div>
			<span class="material-symbols-outlined text-primary">account_balance_wallet</span>
		</div>
		<div
			class="rounded-md border border-outline-variant/30 divide-y divide-outline-variant/20 text-sm"
		>
			<div class="flex items-start justify-between gap-3 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Subtotal</p>
				<p class="font-medium text-on-surface">
					{{ currency }} {{ Number(summary.subtotal || 0).toFixed(2) }}
				</p>
			</div>
			<div class="flex items-start justify-between gap-3 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Paid</p>
				<p class="font-medium text-on-surface">
					{{ currency }} {{ Number(summary.paidAmount || 0).toFixed(2) }}
				</p>
			</div>
			<div class="flex items-start justify-between gap-3 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Outstanding</p>
				<p class="font-medium text-on-surface text-warning">
					{{ currency }} {{ Number(summary.outstandingAmount || 0).toFixed(2) }}
				</p>
			</div>
			<div
				class="flex items-start justify-between gap-3 px-3 py-2.5 bg-surface-container-high font-semibold"
			>
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Total</p>
				<p class="text-on-surface">
					{{ currency }} {{ Number(summary.grandTotal || 0).toFixed(2) }}
				</p>
			</div>
		</div>
	</section>
</template>

<script setup>
defineProps({
	summary: { type: Object, required: true },
	currency: { type: String, default: "KES" },
});
</script>
