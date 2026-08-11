<template>
	<aside
		class="hidden xl:flex flex-col w-80 border-l border-outline-variant bg-surface p-5 space-y-6"
	>
		<section class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
			<h3 class="text-[12px] font-semibold uppercase tracking-wider text-on-surface-variant">
				Workspace Snapshot
			</h3>
			<div class="grid grid-cols-3 gap-3 mt-3 text-center">
				<div class="rounded-lg bg-surface-container p-3">
					<p class="text-[18px] font-bold text-primary">{{ summary.total }}</p>
					<p class="text-[10px] uppercase text-outline">Bookings</p>
				</div>
				<div class="rounded-lg bg-surface-container p-3">
					<p class="text-[18px] font-bold text-tertiary">{{ summary.pendingPayment }}</p>
					<p class="text-[10px] uppercase text-outline">Pending</p>
				</div>
				<div class="rounded-lg bg-surface-container p-3">
					<p class="text-[18px] font-bold text-secondary-ink">{{ summary.checkedIn }}</p>
					<p class="text-[10px] uppercase text-outline">Checked In</p>
				</div>
			</div>
		</section>
		<section class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
			<h3
				class="text-[12px] font-semibold uppercase tracking-wider text-on-surface-variant mb-3"
			>
				Pending Payments
			</h3>
			<div class="space-y-2 max-h-80 overflow-y-auto">
				<div
					v-for="booking in pendingPaymentBookings"
					:key="booking.id"
					class="rounded-lg border border-outline-variant bg-surface p-3"
				>
					<p class="text-[12px] font-semibold">{{ booking.customerName }}</p>
					<p class="text-[11px] text-on-surface-variant">#{{ booking.bookingId }}</p>
					<p class="text-[12px] font-semibold text-tertiary mt-1">
						{{ booking.currency }} {{ booking.outstandingAmount.toFixed(2) }}
					</p>
				</div>
				<p
					v-if="!pendingPaymentBookings.length"
					class="text-[12px] text-on-surface-variant"
				>
					No pending payment bookings.
				</p>
			</div>
		</section>
	</aside>
</template>

<script setup>
defineProps({
	summary: { type: Object, required: true },
	pendingPaymentBookings: { type: Array, default: () => [] },
});
</script>
