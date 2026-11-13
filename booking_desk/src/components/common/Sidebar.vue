<template>
	<aside
		class="h-screen w-64 bg-primary border-r border-primary-dark flex flex-col shrink-0 text-white shadow-xl shadow-primary/10"
	>
		<RouterLink
			:to="{ name: 'Home' }"
			class="h-24 flex items-center px-5 border-b border-white/20 group focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-inset"
			:aria-label="`${branding.company} booking desk`"
		>
			<img
				class="h-[72px] w-full object-contain object-left transition-transform duration-300 group-hover:scale-[1.02]"
				:src="branding.sidebarLogo"
				:alt="`${branding.company} logo`"
			/>
		</RouterLink>

		<div v-if="workspace.showSwitcher" class="px-3 pt-3">
			<WorkspaceSwitcher />
		</div>

		<nav
			class="overflow-y-auto flex-1 p-3 space-y-1 no-scrollbar"
			:aria-label="workspace.current?.label"
		>
			<SidebarItem
				v-for="item in items"
				:key="item.label"
				:to="item.to"
				:activeWhen="item.activeWhen"
				:icon="item.icon"
				:label="item.label"
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
import { computed } from "vue";
import { branding } from "@/branding";
import { useAuthStore } from "@/stores/auth";
import { HOTEL, SERVICES, useWorkspaceStore } from "@/stores/workspace.store";
import { useHotelStore } from "@/stores/hotel.store";
import SidebarItem from "./SidebarItem.vue";
import WorkspaceSwitcher from "./WorkspaceSwitcher.vue";

const auth = useAuthStore();
const workspace = useWorkspaceStore();
const hotel = useHotelStore();

const NAVIGATION = {
	[SERVICES]: [
		{
			label: "Today",
			icon: "dashboard",
			to: { name: "Dashboard" },
			activeWhen: ["Dashboard"],
		},
		{
			label: "Services",
			icon: "spa",
			to: { name: "Services" },
			activeWhen: ["Services", "NewBooking", "GuestAssignment", "Checkout"],
		},
		{
			label: "Appointments",
			icon: "event_note",
			to: { name: "Bookings" },
			activeWhen: ["Bookings", "BookingDetails", "AppointmentDetails"],
		},
	],
	[HOTEL]: [
		{
			label: "New Reservation",
			icon: "add_box",
			to: { name: "NewReservation" },
			activeWhen: ["NewReservation"],
		},
		{
			label: "Front Desk",
			icon: "concierge",
			to: { name: "FrontDeskToday" },
			activeWhen: ["FrontDeskToday", "FrontDeskStay", "HotelStay"],
		},
		{
			label: "Reservations",
			icon: "book_online",
			to: { name: "HotelBookings" },
			activeWhen: ["HotelBookings", "HotelBooking"],
		},
		{
			label: "Cashier",
			icon: "point_of_sale",
			to: { name: "Cashier" },
			activeWhen: ["Cashier"],
			roles: [
				"System Manager",
				"Hospitality Manager",
				"Cashier",
				"Front Desk Manager",
				"Front Desk Agent",
			],
		},
		{
			label: "House Accounts",
			icon: "storefront",
			to: { name: "HotelHouseAccounts" },
			activeWhen: ["HotelHouseAccounts", "HotelHouseAccountFolios"],
			roles: [
				"System Manager",
				"Hospitality Manager",
				"Front Desk Manager",
				"Front Desk Agent",
				"Cashier",
				"Hotel Accountant",
			],
		},
		{
			label: "Night Audit",
			icon: "nights_stay",
			to: { name: "NightAudit" },
			activeWhen: ["NightAudit"],
			roles: ["System Manager", "Hospitality Manager", "Night Auditor"],
		},
	],
};

// An item with `roles` shows only to users with one of them.
const items = computed(() =>
	(NAVIGATION[workspace.active] || []).filter(
		(item) => !item.roles || item.roles.some((role) => hotel.roles.includes(role))
	)
);

async function handleLogout() {
	await auth.logout();
	window.location.reload();
}
</script>
