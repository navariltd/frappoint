<template>
	<div class="flex h-screen overflow-hidden bg-background text-on-surface">
		<Sidebar />

		<div class="flex-1 flex flex-col overflow-hidden">
			<Topbar />

			<main class="flex-1 overflow-y-auto bg-background">
				<router-view />
			</main>
		</div>

		<SessionExpiredDialog />
	</div>
</template>

<script setup>
import Sidebar from "./components/common/Sidebar.vue";
import Topbar from "./components/common/Topbar.vue";
import SessionExpiredDialog from "./components/common/SessionExpiredDialog.vue";
</script>
