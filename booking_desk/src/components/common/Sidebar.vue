<template>
	<aside
		class="h-screen w-64 bg-primary border-r border-primary-dark flex flex-col shrink-0 text-white shadow-xl shadow-primary/10"
	>
		<RouterLink
			:to="{ name: 'Dashboard' }"
			class="h-24 flex items-center px-5 border-b border-white/20 group focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-inset"
			:aria-label="`${branding.company} booking desk`"
		>
			<img
				class="h-[72px] w-full object-contain object-left transition-transform duration-300 group-hover:scale-[1.02]"
				:src="branding.sidebarLogo"
				:alt="`${branding.company} logo`"
			/>
		</RouterLink>

		<nav class="overflow-y-auto flex-1 p-3 space-y-1 no-scrollbar">
			<SidebarItem
				:to="{ name: 'Dashboard' }"
				:activeWhen="['Dashboard']"
				icon="dashboard"
				label="Dashboard"
			/>
			<SidebarItem
				:to="{ name: 'Services' }"
				:activeWhen="['Services', 'NewBooking', 'GuestAssignment', 'Checkout']"
				icon="spa"
				label="Services"
			/>
			<SidebarItem
				:to="{ name: 'Bookings' }"
				:activeWhen="['Bookings', 'BookingDetails', 'AppointmentDetails']"
				icon="event_note"
				label="Bookings"
			/>
		</nav>

		<div class="p-4 border-t border-white/20">
			<button
				@click="handleLogout"
				class="w-full flex items-center gap-3 px-3 py-2.5 text-white/90 hover:bg-white/10 hover:text-white rounded-md transition-colors group focus-visible:ring-2 focus-visible:ring-secondary"
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
import { branding } from "@/branding";
import { useAuthStore } from "@/stores/auth";
import SidebarItem from "./SidebarItem.vue";

const auth = useAuthStore();

async function handleLogout() {
	await auth.logout();
	window.location.reload();
}
</script>
