<template>
	<div
		class="rounded-xl border border-outline-variant bg-surface-container-lowest p-8 text-center"
	>
		<p class="text-[14px] font-semibold text-on-surface">No bookings found</p>
		<p class="text-[12px] text-on-surface-variant mt-1">
			Adjust filters or create a new booking.
		</p>
		<button
			type="button"
			class="mt-4 rounded-lg bg-primary text-on-primary px-4 py-2 text-[12px] font-semibold"
			@click="$emit('quick-booking')"
		>
			Create Booking
		</button>
	</div>
</template>

<script setup>
defineEmits(["quick-booking"]);
</script>
