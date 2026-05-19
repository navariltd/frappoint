<template>
	<form class="grid grid-cols-1 md:grid-cols-3 gap-2" @submit.prevent="onSave">
		<input
			v-model="fullName"
			type="text"
			placeholder="Guest full name"
			required
			class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px]"
		/>
		<input
			v-model="email"
			type="email"
			placeholder="Email (optional)"
			class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px]"
		/>
		<input
			v-model="mobileNo"
			type="text"
			placeholder="Phone (optional)"
			class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px]"
		/>
		<div class="md:col-span-3 flex justify-end gap-2">
			<button
				type="button"
				class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px]"
				@click="$emit('cancel')"
			>
				Cancel
			</button>
			<button
				type="submit"
				class="rounded-lg bg-primary px-3 py-1.5 text-[12px] text-on-primary"
			>
				Save Guest
			</button>
		</div>
	</form>
</template>

<script setup>
import { ref } from "vue";

const emit = defineEmits(["save", "cancel"]);

const fullName = ref("");
const email = ref("");
const mobileNo = ref("");

const onSave = () => {
	emit("save", {
		fullName: fullName.value,
		email: email.value,
		mobileNo: mobileNo.value,
	});
	fullName.value = "";
	email.value = "";
	mobileNo.value = "";
};
</script>
