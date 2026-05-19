<template>
	<section
		class="rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-wider text-outline">
					Financial snapshot
				</p>
				<h2 class="mt-1 text-lg font-semibold text-on-surface">Payment summary</h2>
			</div>
			<span class="material-symbols-outlined text-primary">payments</span>
		</div>
		<div class="space-y-2 text-sm">
			<div class="flex items-center justify-between gap-3">
				<span class="text-on-surface-variant">Total</span>
				<span class="font-semibold text-on-surface"
					>{{ currency }} {{ totalAmount.toFixed(2) }}</span
				>
			</div>
			<div class="flex items-center justify-between gap-3">
				<span class="text-on-surface-variant">Paid</span>
				<span class="font-semibold text-success"
					>{{ currency }} {{ paidAmount.toFixed(2) }}</span
				>
			</div>
			<div
				class="flex items-center justify-between gap-3 border-t border-outline-variant/30 pt-3"
			>
				<span class="font-semibold text-on-surface">Outstanding</span>
				<span class="font-semibold text-primary"
					>{{ currency }} {{ outstandingAmount.toFixed(2) }}</span
				>
			</div>
		</div>
		<div class="flex flex-wrap gap-2">
			<span
				class="px-3 py-1 rounded-full bg-surface-container-high text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant"
			>
				{{ appointment.paymentStatus || "Unpaid" }}
			</span>
			<span
				class="px-3 py-1 rounded-full bg-surface-container-high text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant"
			>
				{{ paymentCount }} payment{{ paymentCount === 1 ? "" : "s" }}
			</span>
		</div>
	</section>
</template>

<script setup>
defineProps({
	appointment: { type: Object, required: true },
	currency: { type: String, default: "KES" },
	totalAmount: { type: Number, default: 0 },
	paidAmount: { type: Number, default: 0 },
	outstandingAmount: { type: Number, default: 0 },
	paymentCount: { type: Number, default: 0 },
});
</script>
