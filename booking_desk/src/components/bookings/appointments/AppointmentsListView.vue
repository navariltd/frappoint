<template>
	<div
		class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4"
	>
		<AppointmentCard
			v-for="appointment in appointments"
			:key="appointment.id"
			:appointment="appointment"
			@open="$emit('open', $event)"
			@checkin="$emit('checkin', $event)"
			@action="$emit('action', $event)"
		/>
	</div>
</template>

<script setup>
import AppointmentCard from "@/components/bookings/appointments/AppointmentCard.vue";

defineProps({
	appointments: { type: Array, default: () => [] },
});

defineEmits(["open", "checkin", "action"]);
</script>
