<template>
	<section
		class="rounded-lg border border-error/30 bg-error-container/10 p-4 shadow-sm space-y-3"
	>
		<div class="flex items-start gap-3">
			<span
				class="material-symbols-outlined text-error text-[18px] mt-0.5 shrink-0"
				style="font-variation-settings: 'FILL' 1"
				>warning</span
			>
			<div class="space-y-2 min-w-0">
				<h4 class="text-[12px] font-semibold uppercase tracking-[0.08em] text-error">
					Operational Alerts
				</h4>
				<p class="text-[13px] text-on-surface-variant leading-relaxed">
					{{ message }}
				</p>
				<ul v-if="alerts.length" class="space-y-1 text-[12px] text-on-surface-variant">
					<li v-for="alert in alerts" :key="alert.id" class="flex items-start gap-2">
						<span
							class="inline-block w-1 h-1 bg-error rounded-full mt-1.5 shrink-0"
						></span>
						{{ alert.message }}
					</li>
				</ul>
			</div>
		</div>
	</section>
</template>

<script setup>
defineProps({
	alerts: { type: Array, default: () => [] },
	message: { type: String, default: "Review booking issues before starting the next service." },
});
</script>
