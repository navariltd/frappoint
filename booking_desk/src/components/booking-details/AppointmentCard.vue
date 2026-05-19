<template>
	<article
		class="bg-surface-container-lowest p-5 rounded-2xl shadow-[0px_4px_20px_rgba(45,52,54,0.05)] border border-outline-variant flex flex-col gap-4 hover:shadow-[0px_12px_32px_rgba(45,52,54,0.08)] transition-all cursor-pointer"
		@click="$emit('open', appointment)"
	>
		<div class="flex items-start justify-between gap-4">
			<div class="flex items-start gap-4 min-w-0">
				<div
					class="size-14 rounded-2xl bg-surface-container-high flex flex-col items-center justify-center shrink-0 border border-outline-variant/30"
				>
					<p class="text-[15px] font-semibold text-on-surface leading-none">
						{{ timeParts.time }}
					</p>
					<p class="text-[10px] text-outline uppercase tracking-wider mt-0.5">
						{{ timeParts.period }}
					</p>
				</div>
				<div class="min-w-0">
					<p class="text-[12px] text-outline font-semibold uppercase tracking-wider">
						Guest &amp; Service
					</p>
					<AppointmentCardHeader :appointment="appointment" />
				</div>
			</div>
			<div class="flex flex-wrap items-center justify-end gap-2 shrink-0">
				<AppointmentOperationalIndicators :appointment="appointment" />
			</div>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
			<div
				class="rounded-xl border border-outline-variant/40 bg-surface-container-low px-4 py-3"
			>
				<p class="text-[11px] uppercase tracking-wider font-semibold text-outline mb-2">
					Provider &amp; Room
				</p>
				<div class="flex items-center gap-2 min-w-0">
					<span class="material-symbols-outlined text-[18px] text-primary">person</span>
					<p class="text-[13px] font-medium text-on-surface truncate">
						{{ appointment.provider }}
					</p>
				</div>
				<AppointmentScheduleInfo :appointment="appointment" :currency="currency" />
			</div>

			<div
				class="rounded-xl border border-outline-variant/40 bg-surface-container-low px-4 py-3 flex flex-col justify-between gap-3"
			>
				<div>
					<p
						class="text-[11px] uppercase tracking-wider font-semibold text-outline mb-2"
					>
						Appointment State
					</p>
					<p class="text-[13px] text-on-surface-variant leading-relaxed">
						{{ appointment.fullName }} is {{ appointment.status.toLowerCase() }} for
						{{ appointment.serviceType }}.
					</p>
				</div>
				<div class="flex items-center justify-between gap-3 flex-wrap">
					<span class="text-[12px] font-semibold text-primary"
						>{{ currency }} {{ Number(appointment.totalAmount || 0).toFixed(2) }}</span
					>
					<div class="flex gap-2">
						<button
							type="button"
							class="p-2.5 text-primary hover:bg-primary/10 rounded-xl border border-primary/20 transition-colors"
							title="Open Appointment"
							@click.stop="$emit('open', appointment)"
						>
							<span class="material-symbols-outlined text-[18px]">open_in_new</span>
						</button>
						<button
							type="button"
							class="bg-primary text-on-primary px-4 py-2.5 rounded-xl text-[12px] font-semibold transition-all hover:opacity-90 active:scale-95"
							@click.stop="$emit('action', 'start', appointment)"
						>
							Start Session
						</button>
					</div>
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
