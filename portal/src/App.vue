<template>
	<div class="min-h-screen bg-background-light">
		<Navbar />
		<router-view />
	</div>
</template>

<script setup>
import Navbar from "./components/Navbar.vue";
</script>
