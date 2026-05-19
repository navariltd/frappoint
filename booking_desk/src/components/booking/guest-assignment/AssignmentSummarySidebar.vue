<template>
	<aside
		class="w-full md:w-80 lg:w-96 bg-surface-container-low border-l border-outline-variant p-4 flex flex-col gap-4"
	>
		<div class="space-y-1 border-b border-outline-variant pb-3">
			<h2 class="text-[14px] font-semibold text-on-surface">Booking Summary</h2>
			<p class="text-[12px] text-on-surface-variant">
				{{ progress.completedGuests }}/{{ progress.totalGuests }} guests scheduled
			</p>
		</div>

		<div class="space-y-2 flex-1 overflow-y-auto pr-1">
			<div
				v-for="row in summaryRows"
				:key="row.guestKey"
				class="rounded-lg border border-outline-variant bg-surface-container-lowest p-2"
			>
				<div class="flex items-center justify-between gap-2">
					<p class="text-[12px] font-semibold">{{ row.guestName }}</p>
					<span
						class="rounded-full px-2 py-1 text-[10px] font-semibold"
						:class="
							row.isComplete
								? 'bg-tertiary-container text-on-tertiary-container'
								: 'bg-secondary-container text-on-secondary-container'
						"
					>
						{{ row.isComplete ? "Ready" : "Pending" }}
					</span>
				</div>
				<p class="text-[11px] text-on-surface-variant">{{ row.serviceName }}</p>
				<p v-if="row.slotLabel" class="text-[11px] text-on-surface-variant">
					{{ row.date }} • {{ row.slotLabel }} • {{ row.providerLabel }}
				</p>
			</div>
		</div>

		<div class="space-y-3 border-t border-outline-variant pt-3">
			<div class="flex items-center justify-between text-[13px] font-semibold">
				<span>Total Estimate</span>
				<span>{{ total }}</span>
			</div>
			<button
				type="button"
				class="w-full rounded-lg px-4 py-3 text-[12px] font-semibold"
				:class="
					isComplete
						? 'bg-primary text-on-primary'
						: 'bg-surface-variant text-on-surface-variant cursor-not-allowed'
				"
				:disabled="!isComplete"
			>
				{{ isComplete ? "Continue to Payment" : "Complete Assignments to Continue" }}
			</button>
		</div>
	</aside>
</template>

<script setup>
defineProps({
	summaryRows: {
		type: Array,
		default: () => [],
	},
	progress: {
		type: Object,
		required: true,
	},
	total: {
		type: String,
		required: true,
	},
	isComplete: {
		type: Boolean,
		default: false,
	},
});
</script>
