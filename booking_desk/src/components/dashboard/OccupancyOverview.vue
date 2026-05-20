<template>
	<section
		:class="[
			'rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 shadow-sm flex flex-col',
			panelHeightClass,
		]"
	>
		<div class="shrink-0">
			<h3 class="text-sm font-semibold text-on-surface">Occupancy Levels</h3>
			<p class="text-[11px] text-on-surface-variant mt-1">
				Capacity pressure across providers and resources
			</p>
		</div>

		<div class="mt-3 flex-1 min-h-0 overflow-y-auto pr-1 space-y-4">
			<ProviderOccupancy :rows="providerRows" />
			<RoomOccupancy :rows="resourceRows" />
		</div>
	</section>
</template>

<script setup>
import { computed } from "vue";
import ProviderOccupancy from "@/components/dashboard/ProviderOccupancy.vue";
import RoomOccupancy from "@/components/dashboard/RoomOccupancy.vue";

const props = defineProps({
	providers: { type: Array, default: () => [] },
	appointments: { type: Array, default: () => [] },
	selectedDate: { type: String, default: "" },
	panelHeightClass: { type: String, default: "h-auto" },
});

const providerRows = computed(() => {
	const daily = props.appointments.filter((item) => item.date === props.selectedDate);
	const workdayMinutes = 8 * 60;

	return props.providers
		.map((provider) => {
			const items = daily.filter((entry) => entry.providerId === provider.id);
			const bookedMinutes = items.reduce(
				(sum, item) => sum + Math.round(Number(item.duration || 0) * 60),
				0
			);
			const percent = Math.min(100, Math.round((bookedMinutes / workdayMinutes) * 100));
			const activeCount = items.filter((item) =>
				["checked in", "checked-in", "ongoing", "in progress"].includes(
					String(item.status || "").toLowerCase()
				)
			).length;
			return {
				id: provider.id,
				name: provider.name,
				percent,
				activeCount,
			};
		})
		.sort((a, b) => b.percent - a.percent);
});

const resourceRows = computed(() => {
	const daily = props.appointments.filter((item) => item.date === props.selectedDate);
	const grouped = new Map();

	for (const appointment of daily) {
		const key = appointment.service || "General Service";
		if (!grouped.has(key)) {
			grouped.set(key, { name: key, count: 0, active: 0 });
		}
		const row = grouped.get(key);
		row.count += 1;
		if (
			["checked in", "checked-in", "ongoing", "in progress"].includes(
				String(appointment.status || "").toLowerCase()
			)
		) {
			row.active += 1;
		}
	}

	const maxCount = Math.max(1, ...Array.from(grouped.values()).map((row) => row.count));
	return Array.from(grouped.values())
		.map((row) => ({
			name: row.name,
			occupied: row.count,
			idle: Math.max(0, maxCount - row.count),
			percent: Math.min(100, Math.round((row.count / maxCount) * 100)),
		}))
		.sort((a, b) => b.percent - a.percent);
});
</script>
