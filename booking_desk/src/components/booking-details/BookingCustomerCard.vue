<template>
	<section
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 shadow-sm space-y-3"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
					Customer
				</p>
				<h2 class="mt-1 text-base font-semibold tracking-tight text-on-surface">
					{{ booking.customerName }}
				</h2>
			</div>
			<span class="material-symbols-outlined text-primary">person</span>
		</div>
		<div class="space-y-2.5 text-sm">
			<div class="rounded-md border border-outline-variant/30 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Email</p>
				<p class="mt-1 font-medium text-on-surface break-all">
					{{ booking.email || "-" }}
				</p>
			</div>
			<div class="rounded-md border border-outline-variant/30 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Phone</p>
				<p class="mt-1 font-medium text-on-surface">
					{{ booking.mobileNo || "-" }}
				</p>
			</div>
		</div>
	</section>
</template>

<script setup>
defineProps({ booking: { type: Object, required: true } });
</script>
