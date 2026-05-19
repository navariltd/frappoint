<template>
	<div
		class="bg-error-container/20 border border-error/20 p-4 rounded-2xl flex gap-3 shadow-[0px_4px_20px_rgba(45,52,54,0.05)]"
	>
		<span
			class="material-symbols-outlined text-error text-[20px]"
			style="font-variation-settings: 'FILL' 1"
			>report</span
		>
		<div class="space-y-2">
			<div>
				<h4 class="text-[13px] font-semibold text-error">Operational Alerts</h4>
				<p class="text-[12px] text-on-error-container">{{ message }}</p>
			</div>
			<ul v-if="alerts.length" class="space-y-1 text-[12px] text-on-surface-variant">
				<li v-for="alert in alerts" :key="alert.id">• {{ alert.message }}</li>
			</ul>
		</div>
	</div>
</template>

<script setup>
defineProps({
	alerts: { type: Array, default: () => [] },
	message: { type: String, default: "Review booking issues before starting the next service." },
});
</script>
