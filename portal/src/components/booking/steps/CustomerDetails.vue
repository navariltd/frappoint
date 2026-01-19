<template>
	<div class="w-full p-6 flex flex-col gap-4">
		<h2 class="text-xl font-semibold mb-4">Your Details</h2>

		<FormControl
			:model-value="userDetails.name"
			@update:model-value="updateField('name', $event)"
			type="text"
			label="Full Name"
			placeholder="Enter your full name"
			:disabled="isLoggedIn"
			class="mb-4"
		/>

		<FormControl
			:model-value="userDetails.email"
			@update:model-value="updateField('email', $event)"
			type="email"
			label="Email"
			placeholder="Enter your email"
			:disabled="isLoggedIn"
			class="mb-4"
		/>

		<FormControl
			:model-value="userDetails.phone"
			@update:model-value="updateField('phone', $event)"
			type="text"
			label="Phone Number"
			placeholder="Enter your phone number"
			:disabled="isLoggedIn"
		/>
	</div>
</template>

<script setup>
import { FormControl } from "frappe-ui";

const props = defineProps({
	userDetails: {
		type: Object,
		required: true,
	},
	isLoggedIn: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["update:userDetails"]);

function updateField(field, value) {
	emit("update:userDetails", {
		...props.userDetails,
		[field]: value,
	});
}
</script>
