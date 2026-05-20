<template>
	<div
		class="bg-surface-container-lowest rounded-2xl p-4 shadow-sm border border-outline-variant/30 flex flex-col gap-3 hover:shadow-md transition-shadow"
	>
		<div class="flex justify-between items-start gap-2">
			<span class="text-label-sm text-outline font-mono"
				>#{{ appointment.appointmentId }}</span
			>
			<AppointmentStatusBadge :status="appointment.status" />
		</div>
		<div class="space-y-1">
			<h3 class="font-headline-sm text-[18px] text-on-surface leading-tight">
				{{ appointment.customerName }}
			</h3>
			<p class="text-label-sm text-primary font-medium">{{ appointment.service }}</p>
		</div>
		<div class="flex items-center gap-3 py-2 border-y border-outline-variant/20 my-1">
			<div
				class="w-6 h-6 rounded-full bg-surface-container-highest flex items-center justify-center"
			>
				<span class="material-symbols-outlined text-[14px]">person</span>
			</div>
			<span class="text-label-sm text-on-surface-variant">{{ appointment.provider }}</span>
		</div>
		<div class="flex flex-col gap-1">
			<div class="flex items-center gap-2 text-outline">
				<span class="material-symbols-outlined text-[16px]">schedule</span>
				<span class="text-label-sm"
					>{{ appointment.startTime }} - {{ appointment.endTime }}</span
				>
			</div>
			<div class="flex items-center gap-2 text-outline">
				<span class="material-symbols-outlined text-[16px]">confirmation_number</span>
				<span class="text-label-sm">{{ appointment.bookingId || "N/A" }}</span>
			</div>
		</div>
		<AppointmentQuickActions @action="onAction" />
	</div>
</template>

<script setup>
import AppointmentQuickActions from "@/components/bookings/appointments/AppointmentQuickActions.vue";
import AppointmentStatusBadge from "@/components/bookings/appointments/AppointmentStatusBadge.vue";

const props = defineProps({
	appointment: { type: Object, required: true },
});

const emit = defineEmits(["open", "checkin", "action"]);

function onAction(action) {
	emit("action", { action, appointment: props.appointment });
	if (action === "open") {
		emit("open", props.appointment);
	}
	if (action === "checkin") {
		emit("checkin", props.appointment);
	}
}
</script>
