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
import Navbar from "./components/common/Navbar.vue";
import Footer from "./components/common/Footer.vue";
</script>
