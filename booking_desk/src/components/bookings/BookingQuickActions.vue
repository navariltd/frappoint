<template>
	<div class="flex flex-wrap gap-2 pt-4" :class="wrapperClass">
		<button
			type="button"
			class="flex-1 bg-primary text-on-primary rounded-xl py-2.5 text-[12px] font-semibold transition-all hover:opacity-90"
			@click="$emit('open')"
		>
			Open Booking
		</button>
	</div>
</template>

<script setup>
defineProps({
	wrapperClass: {
		type: String,
		default: "",
	},
});

defineEmits(["open", "collect", "checkin", "reschedule", "cancel"]);
</script>
