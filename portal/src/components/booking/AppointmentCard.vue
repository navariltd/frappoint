<template>
	<div
		:class="[
			'flex items-start gap-4 rounded-xl shadow-sm transition-shadow p-5',
			variant === 'past'
				? 'bg-gray-50 opacity-75 hover:opacity-90'
				: 'bg-white hover:shadow-md',
			variant === 'next' ? 'border-l-4 border-teal-600' : '',
		]"
	>
		<!-- Date Badge -->
		<div class="flex flex-col items-center justify-center min-w-[60px] flex-shrink-0">
			<div
				:class="[
					'text-xs font-medium mb-1',
					variant === 'past' ? 'text-gray-400' : 'text-gray-500',
				]"
			>
				{{ appointmentMonth }}
			</div>
			<div
				:class="[
					'text-2xl font-bold',
					variant === 'past' ? 'text-gray-500' : 'text-gray-900',
				]"
			>
				{{ appointmentDay }}
			</div>
			<div
				v-if="dateLabel"
				:class="[
					'text-xs font-medium mt-1',
					variant === 'past' ? 'text-gray-400' : 'text-teal-600',
				]"
			>
				{{ dateLabel }}
			</div>
		</div>

		<!-- Appointment Details -->
		<div class="flex-1 min-w-0">
			<!-- Service Icon & Time (for next up) -->
			<div v-if="variant === 'next'" class="flex items-center gap-2 mb-2">
				<div class="flex items-center gap-1.5 text-sm text-gray-500">
					<!-- Service Type Icon -->
					<div class="w-5 h-5 bg-blue-100 rounded flex items-center justify-center">
						<svg class="w-3 h-3 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
							<path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
							<path
								fill-rule="evenodd"
								d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<span class="font-medium">Medical</span>
				</div>

				<div class="flex items-center gap-1.5 text-sm text-gray-500">
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
					<span
						>{{ formatTime(appointment.start_time) }} -
						{{ formatTime(appointment.end_time) }}
						<span class="text-gray-400">({{ appointment.duration }} min)</span></span
					>
				</div>
			</div>

			<!-- Service Name -->
			<h4
				:class="[
					'text-base font-semibold mb-2',
					variant === 'past' ? 'text-gray-600' : 'text-gray-900',
				]"
			>
				{{ appointment.appointment_type }}
			</h4>

			<!-- Provider Info -->
			<div
				:class="[
					'flex items-center gap-2 text-sm',
					variant === 'past' ? 'text-gray-500' : 'text-gray-600',
				]"
			>
				<div
					:class="[
						'w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-medium',
						variant === 'past'
							? 'bg-gray-400'
							: 'bg-gradient-to-br from-teal-400 to-teal-600',
					]"
				>
					{{ getInitials(appointment.appointment_provider) }}
				</div>
				<span>with {{ appointment.appointment_provider }}</span>
				<span
					v-if="
						(variant === 'upcoming' || variant === 'past') && appointment.service_type
					"
					class="text-gray-400"
					>• {{ appointment.service_type }}</span
				>
			</div>
		</div>

		<!-- Actions -->
		<div class="flex items-center">
			<!-- Next Up Actions -->
			<div v-if="variant === 'next'" class="flex flex-col gap-2">
				<button
					class="px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
				>
					Reschedule
				</button>
				<button
					class="px-4 py-2 text-gray-600 text-sm font-medium hover:text-red-600 transition-colors"
				>
					Cancel
				</button>
			</div>

			<!-- Upcoming/Past Actions -->
			<div v-else class="flex items-center gap-4">
				<div
					:class="[
						'flex items-center gap-1.5 text-sm',
						variant === 'past' ? 'text-gray-400' : 'text-gray-500',
					]"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
					<span class="font-medium">{{ formatTime(appointment.start_time) }}</span>
				</div>

				<button
					:class="[
						'p-1 transition-colors',
						variant === 'past'
							? 'text-gray-300 hover:text-gray-500'
							: 'text-gray-400 hover:text-gray-600',
					]"
				>
					<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
						<path
							d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z"
						/>
					</svg>
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	appointment: Object,
	variant: {
		type: String,
		default: "upcoming",
	},
});

const formatTime = (time) => {
	if (!time) return "";
	// Convert 24h format to 12h format
	const [hours, minutes] = time.split(":");
	const hour = parseInt(hours);
	const ampm = hour >= 12 ? "PM" : "AM";
	const displayHour = hour % 12 || 12;
	return `${displayHour}:${minutes} ${ampm}`;
};

const getInitials = (name) => {
	if (!name) return "?";
	const parts = name.trim().split(" ");
	if (parts.length >= 2) {
		return (parts[0][0] + parts[1][0]).toUpperCase();
	}
	return name[0].toUpperCase();
};

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
