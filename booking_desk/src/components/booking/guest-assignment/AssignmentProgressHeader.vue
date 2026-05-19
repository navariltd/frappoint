<template>
	<div class="flex items-center justify-between gap-3">
		<div>
			<p class="text-[13px] font-semibold text-on-surface">{{ serviceName }}</p>
			<p class="text-[11px] text-on-surface-variant">
				{{ duration }} min • {{ packageName }}
			</p>
		</div>
		<div class="text-right">
			<p class="text-[11px] text-on-surface-variant">
				{{ completedGuests }}/{{ totalGuests }} done
			</p>
			<span
				class="inline-flex rounded-full px-2 py-1 text-[10px] font-semibold"
				:class="
					completedGuests === totalGuests
						? 'bg-tertiary-container text-on-tertiary-container'
						: 'bg-secondary-container text-on-secondary-container'
				"
			>
				{{ completedGuests === totalGuests ? "Complete" : "In Progress" }}
			</span>
		</div>
	</div>
</template>

<script setup>
defineProps({
	serviceName: {
		type: String,
		required: true,
	},
	packageName: {
		type: String,
		default: "Default",
	},
	duration: {
		type: Number,
		default: 0,
	},
	completedGuests: {
		type: Number,
		default: 0,
	},
	totalGuests: {
		type: Number,
		default: 0,
	},
});
</script>
