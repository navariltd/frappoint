<template>
	<div class="min-h-screen bg-background-light flex">
		<Navbar />
		<div class="flex-1 flex flex-col min-w-0 md:ml-64">
			<main class="flex-1">
				<router-view />
			</main>
		</div>
	</div>
</template>

<script setup>
import Navbar from "./components/common/Navbar.vue";
</script>
