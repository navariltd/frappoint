<template>
	<div class="min-h-screen bg-background-light">
		<Navbar />
		<router-view />
	</div>
</template>

<script setup>
import { watch } from "vue";
import Navbar from "./components/common/Navbar.vue";
import { useBookingStore } from "./stores/bookingStore";

const booking = useBookingStore();
booking.loadFromStorage();

watch(
	() => booking.draft,
	() => booking.saveToStorage(),
	{ deep: true }
);
</script>
