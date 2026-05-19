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
				<span>{{ appointment.serviceType }}</span>
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
