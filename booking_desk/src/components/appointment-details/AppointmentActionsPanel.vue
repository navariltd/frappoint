<template>
	<section
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
					Lifecycle
				</p>
				<h2 class="mt-1 text-base font-semibold tracking-tight text-on-surface">
					Operational actions
				</h2>
			</div>
			<span class="material-symbols-outlined text-primary">tune</span>
		</div>
		<div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
			<button
				class="px-4 py-2.5 rounded-md border border-primary/70 text-primary bg-transparent hover:bg-primary/10 hover:border-primary transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-45 disabled:cursor-not-allowed"
				type="button"
				:disabled="busy || !actions.canCheckIn"
				@click="$emit('check-in')"
			>
				Check in
			</button>
			<button
				class="px-4 py-2.5 rounded-md border border-primary bg-primary text-on-primary hover:bg-primary/90 transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-45 disabled:cursor-not-allowed"
				type="button"
				:disabled="busy || !actions.canStart"
				@click="$emit('start')"
			>
				Start
			</button>
			<button
				class="px-4 py-2.5 rounded-md border border-warning/70 text-warning bg-transparent hover:bg-warning/10 hover:border-warning transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-warning/40 disabled:opacity-45 disabled:cursor-not-allowed"
				type="button"
				:disabled="busy || !actions.canPause"
				@click="$emit('pause')"
			>
				Pause
			</button>
			<button
				class="px-4 py-2.5 rounded-md border border-outline-variant/70 text-on-surface-variant bg-transparent hover:bg-surface-container-high hover:border-outline transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-45 disabled:cursor-not-allowed"
				type="button"
				:disabled="busy || !actions.canResume"
				@click="$emit('resume')"
			>
				Resume
			</button>
			<button
				class="px-4 py-2.5 rounded-md border border-success/60 text-success bg-transparent hover:bg-success/10 hover:border-success transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success/30 disabled:opacity-45 disabled:cursor-not-allowed"
				type="button"
				:disabled="busy || !actions.canComplete"
				@click="$emit('complete')"
			>
				Complete
			</button>
			<button
				v-if="actions.canReschedule"
				class="px-4 py-2.5 rounded-md border border-outline-variant/70 text-on-surface-variant bg-transparent hover:bg-surface-container-high hover:border-outline transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-45 disabled:cursor-not-allowed"
				type="button"
				:disabled="busy || !actions.canReschedule"
				@click="$emit('reschedule')"
			>
				Reschedule
			</button>
			<button
				v-if="actions.canReassignProvider"
				class="px-4 py-2.5 rounded-md border border-outline-variant/70 text-on-surface-variant bg-transparent hover:bg-surface-container-high hover:border-outline transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-45 disabled:cursor-not-allowed"
				type="button"
				:disabled="busy || !actions.canReassignProvider"
				@click="$emit('reassign-provider')"
			>
				Change Service Provider
			</button>
			<button
				class="px-4 py-2.5 rounded-md border border-error/70 text-error bg-transparent hover:bg-error/10 hover:border-error transition-colors shadow-sm hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-error/30 disabled:opacity-45 disabled:cursor-not-allowed"
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

defineEmits([
	"check-in",
	"start",
	"pause",
	"resume",
	"complete",
	"reschedule",
	"reassign-provider",
	"cancel",
]);
</script>
