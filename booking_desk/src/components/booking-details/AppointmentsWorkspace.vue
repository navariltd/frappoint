<template>
	<div class="space-y-4">
		<div class="flex items-center justify-between">
			<h3 class="text-[16px] font-semibold text-on-surface flex items-center gap-2">
				Appointments
				<span
					class="bg-surface-container-highest text-on-surface px-2 py-0.5 rounded-full text-xs"
					>{{ appointments.length }}</span
				>
			</h3>
			<button
				class="text-primary font-semibold flex items-center gap-1 hover:underline"
				@click="$emit('view-log')"
			>
				<span class="material-symbols-outlined text-[20px]">history</span>
				View Log
			</button>
		</div>
		<div
			v-if="!appointments.length"
			class="rounded-xl border border-outline-variant bg-surface-container-lowest p-6 text-[13px] text-on-surface-variant"
		>
			No appointments are linked to this booking.
		</div>
		<div v-else class="space-y-4">
			<AppointmentCard
				v-for="appointment in appointments"
				:key="appointment.id"
				:appointment="appointment"
				:currency="currency"
				@open="$emit('open-appointment', $event)"
				@action="
					(action, selectedAppointment) =>
						$emit('appointment-action', action, selectedAppointment)
				"
			/>
		</div>
	</div>
</template>

<script setup>
import AppointmentCard from "@/components/booking-details/AppointmentCard.vue";

defineProps({
	appointments: { type: Array, default: () => [] },
	currency: { type: String, default: "KES" },
});
defineEmits(["open-appointment", "appointment-action", "view-log"]);
</script>
