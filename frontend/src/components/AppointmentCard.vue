<template>
	<div
		class="bg-white rounded-lg p-5 w-full sm:w-72 shadow-sm hover:shadow-md transition-all duration-200 hover:-translate-y-1 border border-gray-100"
	>
		<div class="flex justify-between items-start gap-3 mb-4">
			<p class="text-gray-500 text-xs font-medium tracking-wide">{{ name }}</p>
			<Badge
				:variant="'subtle'"
				:ref_for="true"
				:theme="statusToColor[status]"
				size="md"
				label="Badge"
				class="shrink-0"
			>
				{{ status }}
			</Badge>
		</div>
		<div class="flex flex-col gap-3">
			<p class="text-gray-900 text-base font-semibold leading-snug">
				{{ appointment_type }} with {{ appointment_provider }}
			</p>
			<div class="flex items-center gap-3 text-gray-600 text-sm">
				<CalendarDays class="w-4 h-4 text-gray-400" />
				<p>{{ appointment_date }}</p>
			</div>
			<div class="flex items-center gap-3 text-gray-600 text-sm">
				<Clock3 class="w-4 h-4 text-gray-400" />
				<p>{{ start_time }} - {{ end_time }}</p>
			</div>
			<div class="flex items-center gap-3 text-gray-600 text-sm">
				<Hourglass class="w-4 h-4 text-gray-400" />
				<p>{{ duration }} Minutes</p>
			</div>
		</div>
	</div>
</template>
<script setup>
import { Badge } from "frappe-ui";
import { CalendarDays, Clock3, Hourglass } from "lucide-vue-next";

const props = defineProps({
	name: String,
	status: String,
	appointment_date: String,
	appointment_provider: String,
	appointment_type: String,
	start_time: String,
	end_time: String,
	duration: Number,
});

const statusToColor = {
	Open: "gray",
	Confirmed: "blue",
	Completed: "green",
	Rescheduled: "orange",
	Closed: "red",
	"No Show": "red",
	Cancelled: "red",
};
</script>
