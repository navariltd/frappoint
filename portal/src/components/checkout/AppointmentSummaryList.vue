<template>
	<div class="space-y-3">
		<h3 class="text-label-md font-semibold text-on-surface-variant uppercase tracking-wider">
			{{ appointments.length }} Appointment{{ appointments.length !== 1 ? "s" : "" }}
		</h3>

		<div
			v-for="(apt, idx) in appointments"
			:key="apt.name || idx"
			class="rounded-lg border border-outline-variant/20 bg-surface-container p-4"
		>
			<div class="flex items-start justify-between gap-3">
				<div class="space-y-0.5">
					<p class="text-body-md font-semibold text-on-surface">
						{{ apt.appointmentType || "Service" }}
					</p>
					<p class="text-body-sm text-on-surface-variant">
						{{ apt.guestName || "Guest" }}
					</p>
					<p class="text-label-sm text-on-surface-variant/80 mt-1">
						<span v-if="apt.date">{{ formatDate(apt.date) }}</span>
						<span v-if="apt.startTime && apt.endTime">
							· {{ apt.startTime }} – {{ apt.endTime }}
						</span>
					</p>
				</div>
				<div class="text-right flex-shrink-0">
					<p class="text-body-md font-semibold text-on-surface">
						{{ formatCurrency(apt.price, apt.currency || currency) }}
					</p>
					<p
						v-if="apt.status"
						class="text-label-xs text-on-surface-variant mt-0.5 capitalize"
					>
						{{ apt.status }}
					</p>
				</div>
			</div>
		</div>

		<div
			v-if="!appointments.length"
			class="py-6 text-center text-body-sm text-on-surface-variant"
		>
			No appointment details available.
		</div>
	</div>
</template>

<script setup lang="ts">
import { formatCurrency } from "@/utils";
import type { CheckoutAppointment } from "@/services/checkout.service";

defineProps<{
	appointments: CheckoutAppointment[];
	currency: string;
}>();

function formatDate(dateStr: string): string {
	if (!dateStr) return "";
	try {
		return new Intl.DateTimeFormat("en-GB", {
			weekday: "short",
			day: "numeric",
			month: "short",
			year: "numeric",
		}).format(new Date(`${dateStr}T00:00:00`));
	} catch {
		return dateStr;
	}
}
</script>
