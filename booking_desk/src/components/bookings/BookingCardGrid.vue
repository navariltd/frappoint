<template>
	<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
		<BookingCard
			v-for="booking in bookings"
			:key="booking.id"
			:booking="booking"
			@open="$emit('open', $event)"
			@collect="$emit('collect', $event)"
			@checkin="$emit('checkin', $event)"
			@reschedule="$emit('reschedule', $event)"
			@cancel="$emit('cancel', $event)"
		/>
	</div>
</template>

<script setup>
import BookingCard from "@/components/bookings/BookingCard.vue";

defineProps({ bookings: { type: Array, default: () => [] } });

defineEmits(["open", "collect", "checkin", "reschedule", "cancel"]);
</script>
