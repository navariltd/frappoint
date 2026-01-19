<template>
	<div class="flex justify-between items-center bg-white/80 p-4 my-4 rounded">
		<div class="flex flex-col justify-center items-center border-2 border-black rounded p-4">
			<p>{{ appointmentMonth }}</p>
			<h2>{{ appointmentDay }}</h2>
			<p v-if="dateLabel" class="text-sm font-medium">
				{{ dateLabel }}
			</p>
		</div>

		<div class="flex flex-col gap-2 justify-center">
			<template v-if="variant === 'next'">
				<div class="flex items-center gap-2">
					<FeatherIcon class="h-4" name="clock" />
					<p>{{ appointment.start_time }} - {{ appointment.end_time }}</p>
					<p>( {{ appointment.duration }} min)</p>
				</div>
			</template>
			<div>
				{{ appointment.appointment_type }}
				<div class="flex gap-2">
					<img src="" alt="user" />
					<span> with {{ appointment.appointment_provider }}</span>
				</div>
			</div>
		</div>
		<div class="flex flex-row gap-6 justify-center">
			<p v-if="variant === 'upcoming'">{{ appointment.start_time }}</p>

			<!-- NEXT UP actions  -->
			<template v-if="variant === 'next'">
				<div class="flex flex-col justify-between gap-6">
					<button class="text-sm font-medium">Reschedule</button>
					<button class="text-sm font-medium text-red-600">Cancel</button>
				</div>
			</template>

			<!-- Upcoming / default  -->
			<FeatherIcon v-else class="h-4 cursor-pointer" name="more-vertical" />
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui";
import { computed } from "vue";

const props = defineProps({
	appointment: Object,
	variant: {
		type: String,
		default: "upcoming",
	},
});

const appointmentDate = computed(() => {
	const d = new Date(props.appointment.appointment_date);
	d.setHours(0, 0, 0, 0);
	return d;
});

const today = computed(() => {
	const d = new Date();
	d.setHours(0, 0, 0, 0);
	return d;
});

const tomorrow = computed(() => {
	const d = new Date(today.value);
	d.setDate(d.getDate() + 1);
	return d;
});

const dateLabel = computed(() => {
	const diff = (appointmentDate.value - today.value) / (1000 * 60 * 60 * 24);

	if (diff === 0) return "Today";
	if (diff === 1) return "Tomorrow";
	if (diff < 7) return `In ${diff} days`;
	return null;
});

const appointmentMonth = computed(() =>
	appointmentDate.value.toLocaleString("en-US", { month: "short" }).toUpperCase()
);
const appointmentDay = computed(() => appointmentDate.value.getDate());
</script>
