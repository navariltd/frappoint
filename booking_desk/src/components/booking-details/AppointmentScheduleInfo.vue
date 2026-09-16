<template>
	<div class="space-y-2 text-sm mt-2">
		<div class="flex items-start justify-between gap-3">
			<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Date</p>
			<p class="font-medium text-on-surface text-right">{{ appointment.date || "-" }}</p>
		</div>
		<div class="flex items-start justify-between gap-3">
			<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Time</p>
			<p class="font-medium text-on-surface text-right">
				{{ formatTime(appointment.startTime) || "--:--" }} -
				{{ formatTime(appointment.endTime) || "--:--" }}
			</p>
		</div>
		<div class="flex items-start justify-between gap-3">
			<p class="text-[11px] uppercase tracking-[0.08em] text-outline">Outstanding</p>
			<p class="font-medium text-primary text-right">
				{{ currency }} {{ Number(appointment.outstandingAmount || 0).toFixed(2) }}
			</p>
		</div>
	</div>
</template>

<script setup>
import { formatTime } from "@/utils/formatters";

defineProps({
	appointment: { type: Object, required: true },
	currency: { type: String, default: "KES" },
});
</script>
