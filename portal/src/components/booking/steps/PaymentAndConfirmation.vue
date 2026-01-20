<template>
	<div class="w-full p-6 flex flex-col gap-4">
		<h2 class="text-xl font-semibold mb-4">Payment</h2>
		<p>Show booking summary and payment options here</p>
		<div class="mt-4 border-t border-slate-200 pt-4">
			<p><strong>Service:</strong> {{ booking.draft.serviceType }}</p>
			<p>
				<strong>Date & Time:</strong>
				{{ formatSelectedDate(booking.draft.date) }}
				{{ formatTime(booking.draft.slot?.start_time) }}
			</p>
			<p>
				<strong>Staff:</strong>
				{{ booking.draft.provider || "Any Available" }}
			</p>
			<p><strong>Name:</strong> {{ booking.draft.customer }}</p>
			<p><strong>Email:</strong> {{ booking.draft.email }}</p>
			<p><strong>Phone:</strong> {{ booking.draft.mobileNo }}</p>
			<p>
				<strong>Price:</strong>
				{{ formatCurrency(booking.draft.price, booking.draft.currency) }}
			</p>
		</div>
	</div>
</template>

<script setup>
import { useBookingStore } from "@/stores/bookingStore";
import { formatCurrency } from "@/utils";

const booking = useBookingStore();

function formatTime(time) {
	if (!time) return "";

	const [h, m] = time.split(":");
	const date = new Date();
	date.setHours(h, m);
	return date.toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
	});
}

function formatSelectedDate(date) {
	if (!date) return "";

	const jsDate = new Date(`${date}T00:00:00`);

	if (isNaN(jsDate.getTime())) return "";

	return jsDate.toLocaleDateString("en-US", {
		weekday: "long",
		month: "long",
		day: "numeric",
	});
}
</script>
