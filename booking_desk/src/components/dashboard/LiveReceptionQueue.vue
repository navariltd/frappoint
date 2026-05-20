<template>
	<section
		:class="[
			'rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 shadow-sm flex flex-col',
			panelHeightClass,
		]"
	>
		<div class="flex items-center justify-between shrink-0">
			<h3 class="text-sm font-semibold text-on-surface">Live Reception Queue</h3>
			<span
				class="px-2.5 py-1 rounded-md bg-primary-container text-on-primary-container text-[10px] font-semibold uppercase tracking-[0.08em]"
			>
				{{ queueItems.length }} Guests
			</span>
		</div>

		<div class="mt-3 flex-1 min-h-0 max-h-[25rem] overflow-y-auto pr-1">
			<div
				v-if="!queueItems.length"
				class="rounded-md border border-outline-variant/30 px-3 py-4 text-xs text-on-surface-variant"
			>
				No active queue for selected date.
			</div>

			<div v-else class="space-y-2.5">
				<div
					v-for="item in queueItems"
					:key="item.id"
					class="rounded-md border px-3 py-2.5 space-y-2 min-h-[5.875rem]"
					:class="
						item.isUrgent
							? 'border-error/40 bg-error-container/10'
							: 'border-outline-variant/30 bg-surface'
					"
				>
					<div class="flex items-start justify-between gap-3">
						<div class="min-w-0">
							<p class="text-[13px] font-semibold text-on-surface truncate">
								{{ item.guestName }}
							</p>
							<p class="text-[11px] text-on-surface-variant truncate">
								{{ item.service }}
							</p>
							<p class="mt-1 text-[11px] text-on-surface-variant">
								{{ item.startTime }} · {{ item.providerName }}
							</p>
						</div>
						<div class="flex flex-col items-end gap-1.5 shrink-0">
							<StatusIndicatorBadges :label="item.status" type="status" />
							<span
								v-if="item.isUrgent"
								class="text-[10px] font-semibold text-error uppercase tracking-[0.08em]"
								>Urgent</span
							>
						</div>
					</div>

					<AppointmentQuickActions
						:appointment="item"
						@check-in="$emit('check-in', $event)"
						@start="$emit('start', $event)"
						@view="$emit('view-details', $event)"
					/>
				</div>
			</div>
		</div>
	</section>
</template>

<script setup>
import { computed } from "vue";
import AppointmentQuickActions from "@/components/dashboard/AppointmentQuickActions.vue";
import StatusIndicatorBadges from "@/components/dashboard/StatusIndicatorBadges.vue";

const props = defineProps({
	appointments: { type: Array, default: () => [] },
	providers: { type: Array, default: () => [] },
	selectedDate: { type: String, default: "" },
	panelHeightClass: { type: String, default: "h-auto" },
});

defineEmits(["check-in", "start", "view-details"]);

const parseMinutes = (timeValue) => {
	const [hh, mm] = String(timeValue || "00:00")
		.split(":")
		.map(Number);
	return (hh || 0) * 60 + (mm || 0);
};

const isQueueCandidate = (appointment) => {
	const status = String(appointment.status || "")
		.trim()
		.toLowerCase();
	return !["completed", "cancelled", "closed", "no show"].includes(status);
};

const providerName = (providerId) => {
	const provider = props.providers.find((entry) => entry.id === providerId);
	return provider?.name || "Unassigned";
};

const queueItems = computed(() => {
	const now = new Date();
	const nowMinutes = now.getHours() * 60 + now.getMinutes();

	return props.appointments
		.filter((appointment) => appointment.date === props.selectedDate)
		.filter(isQueueCandidate)
		.map((appointment) => {
			const startMinutes = parseMinutes(appointment.startTime);
			const status = String(appointment.status || "")
				.trim()
				.toLowerCase();
			const isUrgent =
				nowMinutes > startMinutes + 10 && !["ongoing", "in progress"].includes(status);

			return {
				...appointment,
				providerName: providerName(appointment.providerId),
				isUrgent,
				_sortMinutes: startMinutes,
			};
		})
		.sort((a, b) => a._sortMinutes - b._sortMinutes);
});
</script>
