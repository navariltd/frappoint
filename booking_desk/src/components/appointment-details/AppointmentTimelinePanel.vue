<template>
	<section
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
					Timeline
				</p>
				<h2 class="mt-1 text-base font-semibold tracking-tight text-on-surface">
					Lifecycle log
				</h2>
			</div>
			<span class="material-symbols-outlined text-primary">schedule</span>
		</div>
		<div class="grid grid-cols-1 md:grid-cols-3 gap-2.5">
			<div
				class="rounded-md bg-surface-container border border-outline-variant/20 px-3 py-2.5"
			>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
					Effective time
				</p>
				<p class="mt-1 text-xl font-semibold text-on-surface">
					{{ formatDuration(currentDuration) }}
				</p>
			</div>
			<div
				class="rounded-md bg-surface-container border border-outline-variant/20 px-3 py-2.5"
			>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
					Pause total
				</p>
				<p class="mt-1 text-xl font-semibold text-on-surface">
					{{ formatDuration(totalPauseSeconds) }}
				</p>
			</div>
			<div
				class="rounded-md bg-surface-container border border-outline-variant/20 px-3 py-2.5"
			>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
					Active session
				</p>
				<p class="mt-1 text-sm font-semibold text-on-surface">
					{{ activeSession ? activeSession.logType : "Idle" }}
				</p>
				<p class="text-xs text-on-surface-variant truncate">
					{{ activeSession ? activeSession.startTime : "No open session" }}
				</p>
			</div>
		</div>
		<div class="space-y-2.5">
			<div
				v-for="segment in segments"
				:key="segment.id"
				class="rounded-md border px-3.5 py-3"
				:class="segmentClasses[segment.tone] || segmentClasses.work"
			>
				<div class="flex items-start justify-between gap-3">
					<div>
						<p class="text-sm font-semibold text-on-surface">{{ segment.label }}</p>
						<p class="text-xs text-on-surface-variant">
							{{ segment.startTime || "-" }}
							<span v-if="segment.endTime"> to {{ segment.endTime }}</span>
						</p>
						<p v-if="segment.notes" class="mt-1 text-xs text-on-surface-variant">
							{{ segment.notes }}
						</p>
					</div>
					<div class="text-right">
						<p class="text-sm font-semibold text-on-surface">
							{{ formatDuration(segment.durationSeconds) }}
						</p>
						<p class="text-[10px] uppercase tracking-[0.08em] text-outline">
							{{ segment.isOpen ? "Active" : "Closed" }}
						</p>
					</div>
				</div>
			</div>
			<p v-if="!segments.length" class="text-sm text-on-surface-variant">
				No lifecycle logs recorded yet.
			</p>
		</div>
	</section>
</template>

<script setup>
defineProps({
	segments: { type: Array, default: () => [] },
	currentDuration: { type: Number, default: 0 },
	totalPauseSeconds: { type: Number, default: 0 },
	activeSession: { type: Object, default: null },
});

const segmentClasses = {
	work: "border-primary/20 bg-primary/5",
	pause: "border-warning/30 bg-warning/10",
	end: "border-success/20 bg-success/5",
	checkin: "border-outline-variant/30 bg-surface-container",
};

const formatDuration = (value) => {
	const totalSeconds = Number(value || 0);
	const hours = Math.floor(totalSeconds / 3600);
	const minutes = Math.floor((totalSeconds % 3600) / 60);
	const seconds = totalSeconds % 60;
	return [hours, minutes, seconds].map((part) => String(part).padStart(2, "0")).join(":");
};
</script>
