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
import { watch, onMounted } from "vue";
import Navbar from "./components/common/Navbar.vue";
import Footer from "./components/common/Footer.vue";
import { useBookingStore } from "./stores/bookingStore";
import { useBookingCart } from "./composables/useBookingCart";

const booking = useBookingStore();
const { hydrate: hydrateCart } = useBookingCart();

booking.loadFromStorage();

// Hydrate booking cart from localStorage on app load
onMounted(() => {
	hydrateCart();
});

watch(
	() => booking.draft,
	() => booking.saveToStorage(),
	{ deep: true }
);
</script>
