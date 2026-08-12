<template>
	<div>
		<h4 class="text-[11px] font-bold text-outline uppercase tracking-wider mb-2">
			Appointment Preview
		</h4>
		<ul class="space-y-1">
			<li
				v-for="appointment in visibleAppointments"
				:key="appointment.id"
				class="text-[13px] flex items-center justify-between gap-2"
			>
				<span class="flex items-center gap-1.5 min-w-0">
					<span class="truncate">{{ appointment.serviceType }}</span>
					<span
						v-if="appointment.isCouple"
						class="shrink-0 rounded-full bg-primary-container px-1.5 py-0.5 text-[9px] font-semibold text-on-primary-container"
					>
						Couple
					</span>
				</span>
				<span class="text-[11px] text-outline"
					>{{ appointment.startTime }} • {{ appointment.provider }}</span
				>
			</li>
			<li v-if="remainingCount > 0" class="text-[12px] text-primary font-semibold">
				+{{ remainingCount }} more
			</li>
		</ul>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	appointments: { type: Array, default: () => [] },
	previewCount: { type: Number, default: 2 },
});

const visibleAppointments = computed(() => props.appointments.slice(0, props.previewCount));
const remainingCount = computed(() => Math.max(0, props.appointments.length - props.previewCount));
</script>
