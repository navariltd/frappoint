<template>
	<div
		@click="goToDetails"
		:class="[
			'flex items-start gap-4 rounded-lg sm:rounded-xl shadow-sm transition-shadow p-4 sm:p-5 cursor-pointer',
			variant === 'past'
				? 'bg-gray-50 opacity-75 hover:opacity-90'
				: 'bg-white hover:shadow-md',
		]"
	>
		<div class="flex flex-col items-center justify-center min-w-[60px] flex-shrink-0">
			<div class="text-xs font-medium text-gray-500">{{ bookingMonth }}</div>
			<div class="text-2xl font-bold text-gray-900">{{ bookingDay }}</div>
			<div v-if="dateLabel" class="text-xs text-teal-600 mt-1">{{ dateLabel }}</div>
		</div>

		<div class="flex-1 min-w-0">
			<h4 class="text-sm sm:text-base font-semibold mb-1.5 text-gray-900">
				Booking #{{ booking.name }}
			</h4>
			<div class="flex items-center gap-2 text-xs text-gray-500">
				<span class="font-medium">{{ primaryService }}</span>
				<span class="text-gray-400">•</span>
				<span
					>{{ booking.total_guests || 1 }} guest{{
						booking.total_guests > 1 ? "s" : ""
					}}</span
				>
			</div>
			<div class="mt-2 flex items-center justify-between">
				<div class="text-sm text-gray-700">
					Status: <span class="font-medium">{{ booking.status }}</span>
				</div>
				<div class="text-sm font-semibold text-gray-900">
					{{ formatCurrency(booking.grand_total, booking.currency) }}
				</div>
			</div>
		</div>

		<div class="flex items-center flex-shrink-0">
			<button class="px-3 py-2 bg-white border rounded text-xs text-gray-600">View</button>
		</div>
	</div>
</template>

<script setup>
import { useRouter } from "vue-router";
import { computed } from "vue";

const props = defineProps({
	booking: Object,
	variant: { type: String, default: "upcoming" },
});

const router = useRouter();

const goToDetails = () => {
	router.push({ name: "BookingDetails", params: { id: props.booking.name } });
};

const primaryService = computed(() => {
	try {
		return props.booking.items && props.booking.items.length
			? props.booking.items[0].service_type || "Service"
			: "Service";
	} catch (e) {
		return "Service";
	}
});

const formatCurrency = (amount, currency) => {
	try {
		return new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: currency || "USD",
		}).format(amount || 0);
	} catch (e) {
		return amount || 0;
	}
};

const bookingDate = computed(() => {
	const d = new Date(props.booking.booking_date || props.booking.creation || Date.now());
	d.setHours(0, 0, 0, 0);
	return d;
});

const today = computed(() => {
	const d = new Date();
	d.setHours(0, 0, 0, 0);
	return d;
});
const bookingMonth = computed(() =>
	bookingDate.value.toLocaleString("en-US", { month: "short" }).toUpperCase()
);
const bookingDay = computed(() => bookingDate.value.getDate());
const dateLabel = computed(() => {
	const diff = (bookingDate.value - today.value) / (1000 * 60 * 60 * 24);
	if (diff === 0) return "Today";
	if (diff === 1) return "Tomorrow";
	if (diff < 7 && diff > 1) return `In ${diff} days`;
	return null;
});
</script>
