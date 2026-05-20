<template>
	<section class="space-y-2.5">
		<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
			Room / Resource Occupancy
		</p>
		<div class="space-y-2 max-h-[13rem] overflow-y-auto pr-1">
			<div
				v-for="row in rows"
				:key="row.name"
				class="rounded-md border border-outline-variant/30 px-3 py-2.5 bg-surface min-h-[3.75rem]"
			>
				<div class="flex items-center justify-between gap-3 text-[12px]">
					<p class="font-medium text-on-surface truncate">{{ row.name }}</p>
					<p class="text-on-surface-variant">
						{{ row.occupied }} used · {{ row.idle }} idle
					</p>
				</div>
				<div class="mt-2 h-2 rounded-full bg-surface-container-high overflow-hidden">
					<div
						class="h-full rounded-full bg-secondary"
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
