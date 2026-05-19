<template>
	<section
		class="rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-wider text-outline">
					Lifecycle
				</p>
				<h2 class="mt-1 text-lg font-semibold text-on-surface">Operational actions</h2>
			</div>
			<span class="material-symbols-outlined text-primary">tune</span>
		</div>
		<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
			<button
				class="px-4 py-3 rounded-xl border border-primary text-primary hover:bg-primary/5 disabled:opacity-60"
				type="button"
				:disabled="busy || !actions.canCheckIn"
				@click="$emit('check-in')"
			>
				Check in
			</button>
			<button
				class="px-4 py-3 rounded-xl bg-primary text-on-primary disabled:opacity-60"
				type="button"
				:disabled="busy || !actions.canStart"
				@click="$emit('start')"
			>
				Start
			</button>
			<button
				class="px-4 py-3 rounded-xl border border-outline-variant text-on-surface-variant hover:bg-surface-container-high disabled:opacity-60"
				type="button"
				:disabled="busy || !actions.canComplete"
				@click="$emit('complete')"
			>
				Complete
			</button>
			<button
				class="px-4 py-3 rounded-xl border border-outline-variant text-on-surface-variant hover:bg-surface-container-high disabled:opacity-60"
				type="button"
				:disabled="busy || !actions.canReschedule"
				@click="$emit('reschedule')"
			>
				Reschedule
			</button>
			<button
				class="px-4 py-3 rounded-xl border border-outline-variant text-on-surface-variant hover:bg-surface-container-high disabled:opacity-60"
				type="button"
				:disabled="busy || !actions.canReassignProvider"
				@click="$emit('reassign-provider')"
			>
				Reassign provider
			</button>
			<button
				class="px-4 py-3 rounded-xl border border-error text-error hover:bg-error/5 disabled:opacity-60"
				type="button"
				:disabled="busy || !actions.canCancel"
				@click="$emit('cancel')"
			>
				Cancel
			</button>
		</div>
	</section>
</template>

<script setup>
defineProps({
	actions: { type: Object, default: () => ({}) },
	busy: { type: Boolean, default: false },
});

defineEmits(["check-in", "start", "complete", "reschedule", "reassign-provider", "cancel"]);
</script>
