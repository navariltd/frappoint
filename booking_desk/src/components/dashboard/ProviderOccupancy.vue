<template>
	<section class="space-y-2.5">
		<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
			Provider Occupancy
		</p>
		<div class="space-y-2 max-h-[8.5rem] overflow-y-auto pr-1">
			<div
				v-for="row in rows"
				:key="row.id"
				class="rounded-md border border-outline-variant/30 px-3 py-2.5 bg-surface min-h-[3.75rem]"
			>
				<div class="flex items-center justify-between gap-3 text-[12px]">
					<p class="font-medium text-on-surface truncate">{{ row.name }}</p>
					<p class="text-on-surface-variant">
						{{ row.percent }}% · {{ row.activeCount }} active
					</p>
				</div>
				<div class="mt-2 h-2 rounded-full bg-surface-container-high overflow-hidden">
					<div
						class="h-full rounded-full bg-primary"
						:style="{ width: `${row.percent}%` }"
					></div>
				</div>
			</div>
		</div>
	</section>
</template>

<script setup>
defineProps({
	rows: { type: Array, default: () => [] },
});
</script>
