<template>
	<BookingDialog />
</template>

<script setup lang="ts">
import BookingDialog from "@/components/booking/BookingDialog.vue";
import { ref } from "vue";

const showBookingDialog = ref(true);
</script>
