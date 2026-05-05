<template>
	<aside
		class="h-[calc(100vh-64px)] w-64 bg-surface-light dark:bg-surface-dark border-r border-border-light dark:border-border-dark flex flex-col shrink-0"
	>
		<nav class="overflow-y-auto flex-1 p-3 space-y-1 no-scrollbar">
			<SidebarItem
				:to="{ name: 'Bookings' }"
				icon="calendar_month"
				label="Appointments"
				count=""
			/>
			<SidebarItem :to="{ name: 'Services' }" icon="browse" label="Services" />
		</nav>

		<div class="p-4 border-t border-border-light dark:border-border-dark">
			<button
				@click="handleLogout"
				class="w-full flex items-center gap-3 px-3 py-2.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/10 rounded-lg transition-colors group"
			>
				<span
					class="material-symbols-outlined text-[20px] group-hover:scale-110 transition-transform"
					>logout</span
				>
				<span class="text-sm font-semibold">Log Out</span>
			</button>
		</div>
	</aside>
</template>

<script setup>
import { useAuthStore } from "@/stores/auth";
import SidebarItem from "./SidebarItem.vue";

const auth = useAuthStore();

async function handleLogout() {
	mobileMenuOpen.value = false;
	await auth.logout();
	window.location.reload();
}
</script>
