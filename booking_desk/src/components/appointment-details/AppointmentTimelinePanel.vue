<template>
	<section
		class="rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-wider text-outline">
					Timeline
				</p>
				<h2 class="mt-1 text-lg font-semibold text-on-surface">Lifecycle log</h2>
			</div>
			<span class="material-symbols-outlined text-primary">schedule</span>
		</div>
		<div class="space-y-4">
			<div v-for="event in timeline" :key="event.id" class="flex gap-3">
				<div
					class="mt-1 h-3 w-3 rounded-full"
					:class="dotClasses[event.tone] || dotClasses.neutral"
				></div>
				<div class="min-w-0">
					<p class="font-semibold text-on-surface">{{ event.label }}</p>
					<p class="text-sm text-on-surface-variant break-words">
						{{ event.detail || event.timestamp || "-" }}
					</p>
				</div>
			</div>
		</div>
	</section>
</template>

<script setup>
defineProps({
	timeline: { type: Array, default: () => [] },
});

const dotClasses = {
	success: "bg-success",
	warning: "bg-warning",
	danger: "bg-error",
	info: "bg-primary",
	neutral: "bg-outline-variant",
};
</script>
