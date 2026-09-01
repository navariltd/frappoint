<template>
	<div class="space-y-3">
		<div v-if="monthGroups.length > 1" class="flex flex-wrap gap-2">
			<button
				v-for="group in monthGroups"
				:key="group.key"
				type="button"
				class="rounded-full border px-3 py-1.5 text-[11px]"
				:class="
					activeMonthKey === group.key
						? 'border-primary bg-primary text-on-primary'
						: 'border-outline-variant bg-surface text-on-surface hover:bg-surface-container'
				"
				@click="activeMonthKey = group.key"
			>
				{{ group.label }}
			</button>
		</div>

		<div class="flex flex-wrap gap-2">
			<button
				v-for="dateRow in visibleDates"
				:key="dateRow.date"
				type="button"
				class="rounded-full border px-3 py-1.5 text-[11px]"
				:class="
					selectedDate === dateRow.date
						? 'border-primary bg-primary text-on-primary'
						: 'border-outline-variant bg-surface text-on-surface hover:bg-surface-container'
				"
				@click="$emit('select', dateRow.date)"
			>
				{{ dateRow.label }}
			</button>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
	dates: {
		type: Array,
		default: () => [],
	},
	selectedDate: {
		type: String,
		default: "",
	},
});

defineEmits(["select"]);

const monthFormatter = new Intl.DateTimeFormat("en-US", {
	month: "short",
	year: "numeric",
});

function getMonthMeta(dateValue) {
	if (!dateValue) return null;
	const parsed = new Date(`${dateValue}T00:00:00`);
	if (Number.isNaN(parsed.getTime())) return null;

	const year = parsed.getFullYear();
	const month = parsed.getMonth();
	return {
		key: `${year}-${String(month + 1).padStart(2, "0")}`,
		label: monthFormatter.format(parsed),
	};
}

const monthGroups = computed(() => {
	const groups = [];
	const seen = new Set();

	for (const dateRow of props.dates) {
		const meta = getMonthMeta(dateRow?.date);
		if (!meta || seen.has(meta.key)) continue;
		seen.add(meta.key);
		groups.push(meta);
	}

	return groups;
});

const activeMonthKey = ref("");

watch(
	() => [props.dates, props.selectedDate],
	([dates, selectedDate]) => {
		const selectedMonthKey = getMonthMeta(selectedDate)?.key;
		const availableKeys = new Set(
			(dates || []).map((dateRow) => getMonthMeta(dateRow?.date)?.key).filter(Boolean)
		);

		if (selectedMonthKey && availableKeys.has(selectedMonthKey)) {
			activeMonthKey.value = selectedMonthKey;
			return;
		}

		if (!availableKeys.has(activeMonthKey.value)) {
			activeMonthKey.value = monthGroups.value[0]?.key || "";
		}
	},
	{ immediate: true }
);

const visibleDates = computed(() => {
	if (!activeMonthKey.value) return props.dates;
	return props.dates.filter((dateRow) => getMonthMeta(dateRow?.date)?.key === activeMonthKey.value);
});
</script>
