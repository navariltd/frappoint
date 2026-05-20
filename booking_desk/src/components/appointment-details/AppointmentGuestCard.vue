<template>
	<section
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
					Guest
				</p>
				<h2 class="mt-1 text-base font-semibold tracking-tight text-on-surface">
					{{ appointment.fullName || appointment.customerName || "Guest" }}
				</h2>
			</div>
			<span class="material-symbols-outlined text-primary">person</span>
		</div>
		<div class="space-y-3 text-sm">
			<div class="rounded-md border border-outline-variant/30 px-3 py-2.5">
				<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Customer</p>
				<p class="mt-1 font-medium text-on-surface">
					{{ appointment.customer || appointment.customerName || "-" }}
				</p>
			</div>
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<div class="rounded-md border border-outline-variant/30 px-3 py-2.5">
					<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Email</p>
					<p class="mt-1 font-medium text-on-surface break-all">
						{{ appointment.email || "-" }}
					</p>
				</div>
				<div class="rounded-md border border-outline-variant/30 px-3 py-2.5">
					<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Phone</p>
					<p class="mt-1 font-medium text-on-surface">
						{{ appointment.mobileNo || "-" }}
					</p>
				</div>
			</div>
			<div
				v-if="appointment.notes"
				class="rounded-md border border-outline-variant/30 bg-surface px-3 py-2.5 text-sm text-on-surface-variant"
			>
				{{ appointment.notes }}
			</div>
		</div>
	</section>
</template>

<script setup>
defineProps({
	appointment: { type: Object, required: true },
});
</script>
