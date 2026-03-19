<template>
	<div class="flex h-screen flex-col overflow-hidden bg-background-light">
		<Topbar />

		<div class="flex-1 flex overflow-hidden">
			<Sidebar />
			<main class="flex-1 overflow-y-auto p-4 bg-gray-50/50">
				<router-view />
			</main>
			<router-view v-slot="{ Component }" name="sidebar">
				<transition
					enter-active-class="transition duration-300 ease-out"
					enter-from-class="translate-x-full opacity-0"
					enter-to-class="translate-x-0 opacity-100"
					leave-active-class="transition duration-200 ease-in"
					leave-from-class="translate-x-0 opacity-100"
					leave-to-class="translate-x-full opacity-0"
				>
					<aside
						v-if="Component"
						class="w-80 bg-white border-l border-border-light dark:border-border-dark flex flex-col shrink-0 shadow-sm"
					>
						<component :is="Component" />
					</aside>
				</transition>
			</router-view>
		</div>
	</div>
</template>

<script setup>
import Sidebar from "./components/common/Sidebar.vue";
import Topbar from "./components/common/Topbar.vue";
</script>
