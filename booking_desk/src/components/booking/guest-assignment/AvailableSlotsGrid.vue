<template>
	<div class="space-y-3">
		<div v-if="timeGroups.length > 1" class="flex flex-wrap gap-2">
			<button
				v-for="group in timeGroups"
				:key="group.key"
				type="button"
				class="rounded-full border px-3 py-1.5 text-[11px] transition-colors"
				:class="
					activeGroupKey === group.key
						? 'border-secondary bg-secondary text-on-secondary'
						: 'border-secondary/30 bg-secondary/10 text-secondary-ink hover:bg-secondary/20'
				"
				:style="groupButtonStyle(group.key)"
				@click="activeGroupKey = group.key"
			>
				{{ group.label }}
			</button>
		</div>

		<div class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
			<SlotCard
				v-for="slot in visibleSlots"
				:key="slot.id"
				:slot="slot"
				:selected="selectedSlotId === slot.id || pendingSlotId === slot.id"
				:pending="pendingSlotId === slot.id"
				:disabled="disabled"
				@select="$emit('select-slot', $event)"
			/>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { branding } from "@/branding";
import SlotCard from "./SlotCard.vue";

const props = defineProps({
	slots: {
		type: Array,
		default: () => [],
	},
	selectedSlotId: {
		type: String,
		default: "",
	},
	pendingSlotId: {
		type: String,
		default: "",
	},
	disabled: {
		type: Boolean,
		default: false,
	},
});

defineEmits(["select-slot"]);

const TIME_GROUPS = [
	{ key: "morning", label: "Morning" },
	{ key: "afternoon", label: "Afternoon" },
	{ key: "evening", label: "Evening" },
];

function toHour(timeValue) {
	const normalized = String(timeValue || "").trim();
	if (!normalized) return null;
	const [hoursPart] = normalized.split(":");
	const hours = Number.parseInt(hoursPart, 10);
	return Number.isFinite(hours) ? hours : null;
}

function getTimeGroupKey(slot) {
	const hour = toHour(slot?.startTime);
	if (hour === null) return null;
	if (hour < 12) return "morning";
	if (hour < 17) return "afternoon";
	return "evening";
}

const timeGroups = computed(() => {
	const availableGroupKeys = new Set(props.slots.map((slot) => getTimeGroupKey(slot)).filter(Boolean));
	return TIME_GROUPS.filter((group) => availableGroupKeys.has(group.key));
});

const activeGroupKey = ref("");

watch(
	() => [props.slots, props.selectedSlotId],
	([slots, selectedSlotId]) => {
		const selectedSlot = (slots || []).find((slot) => slot.id === selectedSlotId);
		const selectedGroupKey = getTimeGroupKey(selectedSlot);
		const availableKeys = new Set((slots || []).map((slot) => getTimeGroupKey(slot)).filter(Boolean));

		if (selectedGroupKey && availableKeys.has(selectedGroupKey)) {
			activeGroupKey.value = selectedGroupKey;
			return;
		}

		if (!availableKeys.has(activeGroupKey.value)) {
			activeGroupKey.value = timeGroups.value[0]?.key || "";
		}
	},
	{ immediate: true }
);

const visibleSlots = computed(() => {
	if (!activeGroupKey.value) return props.slots;
	return props.slots.filter((slot) => getTimeGroupKey(slot) === activeGroupKey.value);
});

function groupButtonStyle(groupKey) {
	if (!branding.accentColor) {
		return null;
	}

	if (activeGroupKey.value === groupKey) {
		return {
			backgroundColor: branding.accentColor,
			borderColor: branding.accentColor,
		};
	}

	return {
		borderColor: `${branding.accentColor}4d`,
		backgroundColor: `${branding.accentColor}1a`,
	};
}
</script>
