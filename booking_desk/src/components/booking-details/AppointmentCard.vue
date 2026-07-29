<template>
	<article
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 shadow-sm hover:shadow-md transition-all cursor-pointer"
		@click="$emit('open', appointment)"
	>
		<div class="flex flex-col gap-4">
			<div class="flex items-start justify-between gap-4">
				<div class="flex items-start gap-3 min-w-0 flex-1">
					<div
						class="size-12 rounded-md bg-surface-container-high flex flex-col items-center justify-center shrink-0 border border-outline-variant/30"
					>
						<p class="text-[13px] font-semibold text-on-surface leading-none">
							{{ timeParts.time }}
						</p>
						<p class="text-[9px] text-outline uppercase tracking-wider mt-0.5">
							{{ timeParts.period }}
						</p>
					</div>
					<div class="min-w-0 flex-1">
						<p
							class="text-[11px] text-outline font-semibold uppercase tracking-[0.08em]"
						>
							Guest &amp; Service
						</p>
						<AppointmentCardHeader :appointment="appointment" />
					</div>
				</div>
				<div class="flex items-center justify-end gap-1.5 shrink-0">
					<AppointmentOperationalIndicators :appointment="appointment" />
				</div>
			</div>

			<div class="space-y-3">
				<div class="rounded-md border border-outline-variant/30 px-3 py-2.5">
					<p
						class="text-[11px] uppercase tracking-[0.08em] font-semibold text-outline mb-2"
					>
						Provider
					</p>
					<p class="text-sm font-medium text-on-surface">
						{{ appointment.provider || "Unassigned" }}
					</p>
				</div>
				<div class="rounded-md border border-outline-variant/30 px-3 py-2.5">
					<p
						class="text-[11px] uppercase tracking-[0.08em] font-semibold text-outline mb-1"
					>
						Time Slot
					</p>
					<AppointmentScheduleInfo :appointment="appointment" :currency="currency" />
				</div>
			</div>

			<div
				class="flex items-center justify-between gap-3 pt-2 border-t border-outline-variant/20"
			>
				<div>
					<p class="text-[10px] uppercase tracking-[0.08em] text-outline">Amount</p>
					<p class="text-sm font-semibold text-primary mt-0.5">
						{{ currency }} {{ Number(appointment.totalAmount || 0).toFixed(2) }}
					</p>
				</div>
				<div class="flex gap-1.5">
					<button
						type="button"
						class="p-2 text-primary hover:bg-primary/10 rounded-md border border-primary/30 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40"
						title="Open Appointment"
						@click.stop="$emit('open', appointment)"
					>
						<span class="material-symbols-outlined text-[18px]">open_in_new</span>
					</button>
					<button
						type="button"
						class="bg-primary text-on-primary px-3.5 py-2 rounded-md text-[12px] font-semibold transition-colors hover:bg-primary-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40 active:scale-95"
						@click.stop="$emit('action', 'start', appointment)"
					>
						Start
					</button>
				</div>
			</div>
		</div>
	</article>
</template>

<script setup>
import { computed } from "vue";
import AppointmentCardHeader from "@/components/booking-details/AppointmentCardHeader.vue";
import AppointmentOperationalIndicators from "@/components/booking-details/AppointmentOperationalIndicators.vue";
import AppointmentScheduleInfo from "@/components/booking-details/AppointmentScheduleInfo.vue";

const props = defineProps({
	appointment: { type: Object, required: true },
	currency: { type: String, default: "KES" },
});

defineEmits(["open", "action"]);

const timeParts = computed(() => {
	const time = String(props.appointment.startTime || "").trim();
	if (!time) return { time: "--:--", period: "" };
	const [hoursPart, minutesPart] = time.split(":");
	const hours = Number(hoursPart);
	const period = hours >= 12 ? "PM" : "AM";
	const displayHours = ((hours + 11) % 12) + 1;
	return {
		time: `${String(displayHours).padStart(2, "0")}:${String(
			Number(minutesPart || 0)
		).padStart(2, "0")}`,
		period,
	};
});
</script>
