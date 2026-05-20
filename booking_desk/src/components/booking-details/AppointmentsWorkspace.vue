<template>
	<section class="space-y-4">
		<div class="flex items-center justify-between gap-3">
			<div class="flex items-center gap-2">
				<h2 class="text-base font-semibold text-on-surface">Appointments</h2>
				<span
					class="px-2.5 py-1 rounded-md bg-surface-container-high text-on-surface-variant text-[10px] font-semibold"
				>
					{{ appointments.length }}
				</span>
			</div>
		</div>
		<div
			v-if="!appointments.length"
			class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-6 text-[13px] text-on-surface-variant text-center"
		>
			No appointments are linked to this booking.
		</div>
		<div v-else class="space-y-3">
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
	</section>
</template>

<script setup>
import AppointmentCard from "@/components/booking-details/AppointmentCard.vue";

defineProps({
	appointments: { type: Array, default: () => [] },
	currency: { type: String, default: "KES" },
});
defineEmits(["open-appointment", "appointment-action", "view-log"]);
</script>
