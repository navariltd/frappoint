<template>
	<section
		v-if="alerts.length"
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 shadow-sm space-y-3"
	>
		<div class="flex items-center gap-2 text-outline">
			<span class="material-symbols-outlined">warning</span>
			<h2 class="text-[11px] font-semibold uppercase tracking-[0.08em]">Alerts</h2>
		</div>
		<div class="space-y-2">
			<div
				v-for="alert in alerts"
				:key="alert.id"
				class="rounded-md border px-3 py-2.5"
				:class="toneClasses[alert.severity] || toneClasses.info"
			>
				<p class="text-sm font-semibold">{{ alert.label }}</p>
				<p class="text-xs opacity-90">{{ alert.message }}</p>
			</div>
		</div>
	</section>
</template>

<script setup>
defineProps({
	alerts: { type: Array, default: () => [] },
});

const toneClasses = {
	success: "border-success/30 bg-success/10 text-success",
	warning: "border-warning/30 bg-warning/10 text-warning",
	danger: "border-error/30 bg-error/10 text-error",
	info: "border-primary/30 bg-primary/10 text-primary",
};
</script>
