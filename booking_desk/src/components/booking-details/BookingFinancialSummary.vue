<template>
	<div class="tonal-layer-1 rounded-2xl overflow-hidden border border-outline-variant">
		<div class="bg-surface-container-high p-4 border-b border-outline-variant">
			<h3 class="text-[14px] font-semibold text-on-surface flex items-center gap-2">
				<span class="material-symbols-outlined text-[20px]">account_balance_wallet</span>
				Financial Summary
			</h3>
		</div>
		<div class="p-5 space-y-3 text-[13px]">
			<div class="flex justify-between text-on-surface-variant">
				<span>Subtotal</span>
				<span>{{ currency }} {{ summary.subtotal.toFixed(2) }}</span>
			</div>
			<div class="flex justify-between text-on-surface-variant">
				<span>Paid</span>
				<span>{{ currency }} {{ summary.paidAmount.toFixed(2) }}</span>
			</div>
			<div class="flex justify-between text-on-surface-variant">
				<span>Outstanding</span>
				<span>{{ currency }} {{ summary.outstandingAmount.toFixed(2) }}</span>
			</div>
			<div
				class="pt-3 border-t border-dashed border-outline-variant flex justify-between font-semibold"
			>
				<span>Total Value</span>
				<span>{{ currency }} {{ summary.grandTotal.toFixed(2) }}</span>
			</div>
		</div>
	</div>
</template>

<script setup>
defineProps({
	summary: { type: Object, required: true },
	currency: { type: String, default: "KES" },
});
</script>
