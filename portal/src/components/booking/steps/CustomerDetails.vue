<template>
	<div class="w-full p-6 flex flex-col gap-4">
		<h2 class="text-xl font-semibold mb-4">Your Details</h2>

		<FormControl
			:model-value="booking.draft.customer"
			@update:model-value="booking.setCustomer($event)"
			type="text"
			label="Full Name"
			placeholder="Enter your full name"
			:disabled="isLoggedIn"
			class="mb-4"
		/>

		<FormControl
			:model-value="booking.draft.email"
			@update:model-value="booking.setEmail($event)"
			type="email"
			label="Email"
			placeholder="Enter your email"
			:disabled="isLoggedIn"
			class="mb-4"
		/>

		<FormControl
			:model-value="booking.draft.mobileNo"
			@update:model-value="booking.setMobileNo($event)"
			type="text"
			label="Phone Number"
			placeholder="Enter your phone number"
			:disabled="isLoggedIn"
		/>
	</div>
</template>

<script setup>
import { FormControl } from "frappe-ui";
import { useBookingStore } from "@/stores/bookingStore";

const props = defineProps({
	isLoggedIn: {
		type: Boolean,
		default: false,
	},
});

const booking = useBookingStore();
</script>
