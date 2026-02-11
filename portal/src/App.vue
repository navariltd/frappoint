<template>
	<div class="min-h-screen bg-background-light flex flex-col">
		<Navbar />
		<main class="flex-1">
			<router-view />
		</main>
		<Footer />
	</div>
</template>

<script setup>
import { watch } from "vue";
import Navbar from "./components/common/Navbar.vue";
import Footer from "./components/common/Footer.vue";
import { useBookingStore } from "./stores/bookingStore";

const booking = useBookingStore();
booking.loadFromStorage();

watch(
	() => booking.draft,
	() => booking.saveToStorage(),
	{ deep: true }
);
</script>
