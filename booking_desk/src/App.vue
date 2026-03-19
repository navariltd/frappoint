<template>
	<div class="flex h-screen flex-col overflow-hidden bg-background-light">
		<Topbar />

		<div class="flex-1 flex overflow-hidden">
			<Sidebar />
			<main class="flex-1 overflow-y-auto p-4">
				<router-view />
			</main>
		</div>
	</div>
</template>

<script setup>
import Sidebar from "./components/common/Sidebar.vue";
import Topbar from "./components/common/Topbar.vue";
</script>
