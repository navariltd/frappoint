<template>
	<AppointmentStatusBadge :status="status" />
</template>

<script setup>
import AppointmentStatusBadge from "@/components/bookings/appointments/AppointmentStatusBadge.vue";

defineProps({
	status: { type: String, default: "Open" },
});
</script>
