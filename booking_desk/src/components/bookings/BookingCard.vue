<template>
	<article
		class="bg-surface-container-lowest p-6 rounded-2xl shadow-[0px_4px_20px_rgba(45,52,54,0.05)] border border-outline-variant flex flex-col gap-4 hover:shadow-[0px_12px_32px_rgba(45,52,54,0.08)] transition-all"
	>
		<BookingCardHeader :booking="booking" />

		<div class="grid grid-cols-2 gap-4 py-3 border-y border-outline-variant/30 text-[13px]">
			<div class="flex items-center gap-2">
				<span class="material-symbols-outlined text-outline text-[18px]">group</span>
				<span>{{ booking.totalGuests }} Guests</span>
			</div>
			<div class="flex items-center gap-2">
				<span class="material-symbols-outlined text-outline text-[18px]"
					>calendar_today</span
				>
				<span>{{ booking.bookingDate || "-" }}</span>
			</div>
			<div class="flex items-center gap-2">
				<span class="material-symbols-outlined text-outline text-[18px]">event_note</span>
				<span>{{ booking.appointmentCount }} Appts</span>
			</div>
			<div class="flex items-center gap-2 text-primary">
				<span class="material-symbols-outlined text-[18px]">schedule</span>
				<span class="font-semibold">{{ upcomingLabel }}</span>
			</div>
		</div>

		<div class="flex-1">
			<BookingAppointmentPreview :appointments="booking.appointments" />
		</div>

		<BookingQuickActions
			class="mt-auto"
			@open="$emit('open', booking)"
			@collect="$emit('collect', booking)"
			@checkin="$emit('checkin', booking)"
			@reschedule="$emit('reschedule', booking)"
			@cancel="$emit('cancel', booking)"
		/>
	</article>
</template>

<script setup>
import { computed } from "vue";
import BookingAppointmentPreview from "@/components/bookings/BookingAppointmentPreview.vue";
import BookingCardHeader from "@/components/bookings/BookingCardHeader.vue";
import BookingQuickActions from "@/components/bookings/BookingQuickActions.vue";

const props = defineProps({ booking: { type: Object, required: true } });

defineEmits(["open", "collect", "checkin", "reschedule", "cancel"]);

const upcomingLabel = computed(() => {
	const next = props.booking.upcomingAppointment;
	if (!next) {
		return "No upcoming";
	}
	return `${next.startTime || "--:--"}`;
});
</script>
