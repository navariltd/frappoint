<template>
	<div class="flex items-center gap-1.5">
		<button
			v-if="canCheckIn"
			type="button"
			class="rounded-md border border-primary/70 text-primary px-2.5 py-1.5 text-[11px] font-semibold hover:bg-primary/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40"
			@click="$emit('check-in', appointment)"
		>
			Check In
		</button>
		<button
			v-if="canStart"
			type="button"
			class="rounded-md border border-primary bg-primary text-on-primary px-2.5 py-1.5 text-[11px] font-semibold hover:bg-primary-dark transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40"
			@click="$emit('start', appointment)"
		>
			Start
		</button>
		<button
			type="button"
			class="rounded-md border border-outline-variant/70 text-on-surface-variant px-2.5 py-1.5 text-[11px] font-semibold hover:bg-surface-container-high transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/30"
			@click="$emit('view', appointment)"
		>
			Details
		</button>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	appointment: { type: Object, required: true },
});

defineEmits(["check-in", "start", "view"]);

const normalizedStatus = computed(() =>
	String(props.appointment.status || "")
		.trim()
		.toLowerCase()
);

const canCheckIn = computed(() =>
	["open", "confirmed", "pending payment"].includes(normalizedStatus.value)
);
const canStart = computed(() => ["checked in", "checked-in"].includes(normalizedStatus.value));
</script>
