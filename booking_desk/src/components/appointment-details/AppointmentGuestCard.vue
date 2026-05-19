<template>
	<section
		class="rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-wider text-outline">
					Guest
				</p>
				<h2 class="mt-1 text-lg font-semibold text-on-surface">
					{{ appointment.fullName || appointment.customerName || "Guest" }}
				</h2>
			</div>
			<span class="material-symbols-outlined text-primary">person</span>
		</div>
		<div class="space-y-3 text-sm">
			<div class="rounded-xl bg-surface-container px-3 py-3">
				<p class="text-[11px] uppercase tracking-wider text-outline">Customer</p>
				<p class="mt-1 font-semibold text-on-surface">
					{{ appointment.customer || appointment.customerName || "-" }}
				</p>
			</div>
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<div class="rounded-xl bg-surface-container px-3 py-3">
					<p class="text-[11px] uppercase tracking-wider text-outline">Email</p>
					<p class="mt-1 font-semibold text-on-surface break-all">
						{{ appointment.email || "-" }}
					</p>
				</div>
				<div class="rounded-xl bg-surface-container px-3 py-3">
					<p class="text-[11px] uppercase tracking-wider text-outline">Phone</p>
					<p class="mt-1 font-semibold text-on-surface">
						{{ appointment.mobileNo || "-" }}
					</p>
				</div>
			</div>
			<div
				v-if="appointment.notes"
				class="rounded-xl border border-outline-variant/30 bg-surface p-3 text-sm text-on-surface-variant"
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
