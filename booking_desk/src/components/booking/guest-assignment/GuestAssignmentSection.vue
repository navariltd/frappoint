<template>
	<div class="space-y-3">
		<GuestAssignmentRow
			v-for="guest in guests"
			:key="guest.guestKey"
			:guest="guest"
			:quantity="quantity"
			:customers="customers"
			:isLoadingDates="Boolean(isLoadingDates[guest.guestKey])"
			:isLoadingSlots="Boolean(isLoadingSlots[guest.guestKey])"
			:error="errorByGuest[guest.guestKey] || ''"
			@select-customer="$emit('select-customer', guest.guestKey, $event)"
			@quick-create="$emit('quick-create', guest.guestKey, $event)"
			@clear-guest="$emit('clear-guest', guest.guestKey)"
			@load-dates="$emit('load-dates', guest.guestKey)"
			@select-date="$emit('select-date', guest.guestKey, $event)"
			@select-slot="$emit('select-slot', guest.guestKey, $event)"
		/>
	</div>
</template>

<script setup>
import GuestAssignmentRow from "./GuestAssignmentRow.vue";

defineProps({
	guests: {
		type: Array,
		default: () => [],
	},
	quantity: {
		type: Number,
		default: 1,
	},
	customers: {
		type: Array,
		default: () => [],
	},
	isLoadingDates: {
		type: Object,
		default: () => ({}),
	},
	isLoadingSlots: {
		type: Object,
		default: () => ({}),
	},
	errorByGuest: {
		type: Object,
		default: () => ({}),
	},
});

defineEmits([
	"select-customer",
	"quick-create",
	"clear-guest",
	"load-dates",
	"select-date",
	"select-slot",
]);
</script>
