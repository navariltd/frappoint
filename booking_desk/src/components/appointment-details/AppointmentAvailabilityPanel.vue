<template>
	<section
		class="rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-5 shadow-sm space-y-4"
	>
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-wider text-outline">
					Availability
				</p>
				<h2 class="mt-1 text-lg font-semibold text-on-surface">Reschedule slot picker</h2>
			</div>
			<span class="material-symbols-outlined text-primary">calendar_month</span>
		</div>

		<div v-if="dates.length" class="flex flex-wrap gap-2">
			<button
				v-for="date in dates"
				:key="date.date"
				type="button"
				class="px-3 py-2 rounded-full border text-sm transition-colors"
				:class="
					date.date === selectedDate
						? 'border-primary bg-primary text-on-primary'
						: 'border-outline-variant text-on-surface-variant hover:bg-surface-container-high'
				"
				@click="$emit('select-date', date.date)"
			>
				{{ date.label || date.date }}
			</button>
		</div>

		<div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2">
			<button
				v-for="slot in slots"
				:key="slot.id"
				type="button"
				class="rounded-xl border px-3 py-3 text-left transition-colors"
				:class="
					slot.id === selectedSlotId
						? 'border-primary bg-primary/5'
						: 'border-outline-variant hover:bg-surface-container-high'
				"
				@click="$emit('select-slot', slot)"
			>
				<div class="flex items-center justify-between gap-3">
					<div>
						<p class="font-semibold text-on-surface">
							{{ slot.startTime }} - {{ slot.endTime }}
						</p>
						<p class="text-xs text-on-surface-variant">{{ slot.providerSummary }}</p>
					</div>
					<span class="material-symbols-outlined text-primary">event_available</span>
				</div>
			</button>
		</div>

		<div class="flex items-center gap-3">
			<button
				class="px-4 py-2 rounded-full bg-primary text-on-primary disabled:opacity-60"
				type="button"
				:disabled="!selectedSlot || busy"
				@click="$emit('apply-slot')"
			>
				Apply selected slot
			</button>
			<p class="text-sm text-on-surface-variant">
				{{
					selectedSlot
						? `${selectedSlot.startTime} - ${selectedSlot.endTime}`
						: "Select a slot to reschedule."
				}}
			</p>
		</div>
	</section>
</template>

<script setup>
defineProps({
	dates: { type: Array, default: () => [] },
	slots: { type: Array, default: () => [] },
	selectedDate: { type: String, default: "" },
	selectedSlotId: { type: String, default: "" },
	selectedSlot: { type: Object, default: null },
	busy: { type: Boolean, default: false },
});

defineEmits(["select-date", "select-slot", "apply-slot"]);
</script>
