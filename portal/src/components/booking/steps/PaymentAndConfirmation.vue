<template>
	<div class="w-full p-6 flex flex-col gap-4">
		<h2 class="text-xl font-semibold mb-4">Payment</h2>
		<p>Show booking summary and payment options here</p>
		<div class="mt-4 border-t border-slate-200 pt-4">
			<p><strong>Service:</strong> {{ serviceType }}</p>
			<p>
				<strong>Date & Time:</strong>
				{{ formatSelectedDate(selectedDate) }}
				{{ formatTime(selectedSlot?.start_time) }}
			</p>
			<p>
				<strong>Staff:</strong>
				{{ selectedProvider || "Any Available" }}
			</p>
			<p><strong>Name:</strong> {{ userDetails.name }}</p>
			<p><strong>Email:</strong> {{ userDetails.email }}</p>
			<p><strong>Phone:</strong> {{ userDetails.phone }}</p>
			<p><strong>Price:</strong> {{ servicePrice }}</p>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	serviceType: String,
	selectedDate: String,
	selectedSlot: Object,
	selectedProvider: [String, null],
	userDetails: Object,
	servicePrice: String,
});

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
