<template>
	<div class="rounded-xl border border-outline-variant bg-surface p-3 space-y-2">
		<div class="flex items-center justify-between text-[12px]">
			<span class="text-on-surface-variant">Total</span>
			<span class="font-semibold">{{ currency }} {{ totalAmount.toFixed(2) }}</span>
		</div>
		<div class="flex items-center justify-between text-[12px]">
			<span class="text-on-surface-variant">Paid</span>
			<span class="font-semibold">{{ currency }} {{ paidAmount.toFixed(2) }}</span>
		</div>
		<div class="flex items-center justify-between text-[12px]">
			<span class="text-on-surface-variant">Outstanding</span>
			<span class="font-semibold">{{ currency }} {{ outstandingAmount.toFixed(2) }}</span>
		</div>
		<div class="flex items-center justify-between text-[12px]">
			<span class="text-on-surface-variant">Payable now</span>
			<span class="font-semibold text-primary"
				>{{ currency }} {{ payableAmount.toFixed(2) }}</span
			>
		</div>
		<div
			class="flex items-center justify-between text-[12px] pt-1 border-t border-outline-variant"
		>
			<span class="text-on-surface-variant">Remaining after this</span>
			<span class="font-semibold"
				>{{ currency }} {{ remainingAfterPayment.toFixed(2) }}</span
			>
		</div>
	</div>
</template>

<script setup>
defineProps({
	currency: { type: String, default: "KES" },
	totalAmount: { type: Number, default: 0 },
	paidAmount: { type: Number, default: 0 },
	outstandingAmount: { type: Number, default: 0 },
	payableAmount: { type: Number, default: 0 },
	remainingAfterPayment: { type: Number, default: 0 },
});
</script>
