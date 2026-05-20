<template>
	<section
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 shadow-sm space-y-3"
	>
		<div class="flex items-center justify-between">
			<h3 class="text-sm font-semibold text-on-surface">Recent Activity</h3>
			<span class="text-[11px] text-on-surface-variant">Unified event stream</span>
		</div>

		<div
			v-if="!events.length"
			class="rounded-md border border-outline-variant/30 px-3 py-4 text-xs text-on-surface-variant"
		>
			No recent activity available.
		</div>

		<div v-else class="space-y-2">
			<div
				v-for="event in events"
				:key="event.id"
				class="rounded-md border border-outline-variant/30 px-3 py-2.5 bg-surface"
			>
				<div class="flex items-start justify-between gap-3">
					<div class="min-w-0">
						<div class="flex items-center gap-2">
							<StatusIndicatorBadges :label="event.typeLabel" type="event" />
							<p class="text-[11px] text-on-surface-variant">
								{{ event.timeLabel }}
							</p>
						</div>
						<p class="mt-1 text-[13px] font-medium text-on-surface truncate">
							{{ event.title }}
						</p>
						<p class="text-[11px] text-on-surface-variant truncate">
							{{ event.subtitle }}
						</p>
					</div>
				</div>
			</div>
		</div>
	</section>
</template>

<script setup>
import { computed } from "vue";
import StatusIndicatorBadges from "@/components/dashboard/StatusIndicatorBadges.vue";

const props = defineProps({
	appointments: { type: Array, default: () => [] },
	selectedDate: { type: String, default: "" },
});

const parseMinutes = (timeValue) => {
	const [hh, mm] = String(timeValue || "00:00")
		.split(":")
		.map(Number);
	return (hh || 0) * 60 + (mm || 0);
};

const eventFromAppointment = (appointment) => {
	const status = String(appointment.status || "")
		.trim()
		.toLowerCase();
	const paymentPending = Number(appointment.outstandingAmount || 0) > 0;
	const startTime = appointment.startTime || "00:00";
	const base = {
		id: `${appointment.id}-${status}`,
		sortTime: parseMinutes(startTime),
		timeLabel: startTime,
		title: `${appointment.guestName} · ${appointment.service}`,
		subtitle: `Appointment ${appointment.id}`,
	};

	if (paymentPending) {
		return {
			...base,
			id: `${appointment.id}-payment`,
			typeLabel: "Payment Processed",
			subtitle: `${appointment.service} · Pending balance`,
		};
	}
	if (["checked in", "checked-in"].includes(status)) {
		return {
			...base,
			typeLabel: "Check-In",
			subtitle: `${appointment.guestName} checked in`,
		};
	}
	if (["rescheduled"].includes(status)) {
		return {
			...base,
			typeLabel: "Rescheduled",
			subtitle: `${appointment.guestName} moved to ${startTime}`,
		};
	}
	if (["cancelled"].includes(status)) {
		return {
			...base,
			typeLabel: "Cancelled",
			subtitle: `${appointment.guestName} appointment cancelled`,
		};
	}
	return {
		...base,
		typeLabel: "Booking Created",
		subtitle: `${appointment.guestName} scheduled for ${startTime}`,
	};
};

const events = computed(() => {
	return props.appointments
		.filter((appointment) => appointment.date === props.selectedDate)
		.map(eventFromAppointment)
		.sort((a, b) => b.sortTime - a.sortTime)
		.slice(0, 10);
});
</script>
