<template>
	<section
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
					Financial snapshot
				</p>
				<h2 class="mt-1 text-base font-semibold tracking-tight text-on-surface">
					Payment summary
				</h2>
			</div>
			<span class="material-symbols-outlined text-primary">payments</span>
		</div>
		<div
			class="rounded-md border border-outline-variant/30 divide-y divide-outline-variant/20 text-sm"
		>
			<div class="flex items-center justify-between gap-3 px-3 py-2.5">
				<span class="text-on-surface-variant">Total</span>
				<span class="font-medium text-on-surface"
					>{{ currency }} {{ totalAmount.toFixed(2) }}</span
				>
			</div>
			<div class="flex items-center justify-between gap-3 px-3 py-2.5">
				<span class="text-on-surface-variant">Paid</span>
				<span class="font-medium text-success"
					>{{ currency }} {{ paidAmount.toFixed(2) }}</span
				>
			</div>
			<div class="flex items-center justify-between gap-3 px-3 py-2.5">
				<span class="font-semibold text-on-surface">Outstanding</span>
				<span class="font-semibold text-primary"
					>{{ currency }} {{ outstandingAmount.toFixed(2) }}</span
				>
			</div>
		</div>
		<div class="flex flex-wrap gap-1.5">
			<span
				class="px-2.5 py-1 rounded-md bg-surface-container-high text-[10px] font-semibold uppercase tracking-[0.08em] text-on-surface-variant"
			>
				{{ appointment.paymentStatus || "Unpaid" }}
			</span>
			<span
				class="px-2.5 py-1 rounded-md bg-surface-container-high text-[10px] font-semibold uppercase tracking-[0.08em] text-on-surface-variant"
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
