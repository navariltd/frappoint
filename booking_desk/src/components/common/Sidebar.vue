<template>
	<aside
		class="h-[calc(100vh)] w-64 bg-surface-light dark:bg-surface-dark border-r border-border-light dark:border-border-dark flex flex-col shrink-0"
	>
		<RouterLink
			:to="{ name: 'Bookings' }"
			class="h-20 flex items-center gap-3 px-4 border-b border-border-light dark:border-border-dark group"
		>
			<div
				class="flex items-center justify-center rounded-xl bg-white p-1 shadow-sm ring-1 ring-gray-100 dark:ring-gray-800 transition-transform group-hover:scale-105"
			>
				<img
					class="w-10 h-10 object-contain"
					src="../../assets/images/logo_img.png"
					alt="Logo"
				/>
			</div>

			<div class="flex flex-col">
				<h1 class="text-lg font-extrabold leading-tight tracking-tight text-primary">
					Booking<span class="text-text-main-light dark:text-text-main-dark font-medium"
						>Desk</span
					>
				</h1>
			</div>
		</RouterLink>

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
	await auth.logout();
	window.location.reload();
}
</script>
