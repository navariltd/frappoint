<template>
	<header
		class="h-24 bg-surface-light/95 backdrop-blur border-b border-border-light/80 flex items-center justify-between px-6 shrink-0 z-20 shadow-sm"
	>
		<div class="min-w-0 flex-1 pr-4">
			<p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-secondary-ink">
				{{ sectionLabel }}
			</p>
			<div class="mt-1 flex items-center gap-3 min-w-0">
				<h1
					class="truncate text-xl font-extrabold leading-tight tracking-tight text-primary"
				>
					{{ pageTitle }}
				</h1>
				<span
					v-if="pageTag"
					class="shrink-0 rounded-full border border-secondary/20 bg-secondary-container px-2.5 py-1 text-[11px] font-semibold text-on-secondary-container"
				>
					{{ pageTag }}
				</span>
			</div>
			<p class="mt-1 truncate text-[12px] text-text-sub-light dark:text-text-sub-dark">
				{{ pageDescription }}
			</p>
		</div>
		<div class="flex items-center gap-3 md:gap-4 pl-4 shrink-0">
			<div
				v-if="workspace.active === HOTEL && hotel.properties.length"
				class="hidden md:flex items-center gap-2"
			>
				<select
					v-if="hotel.properties.length > 1"
					v-model="propertyName"
					aria-label="Property"
					class="rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] font-semibold text-on-surface"
				>
					<option v-for="p in hotel.properties" :key="p.name" :value="p.name">
						{{ p.property_name }}
					</option>
				</select>
				<span v-else class="text-[13px] font-semibold text-on-surface">
					{{ hotel.currentProperty?.property_name }}
				</span>
				<span
					v-if="hotel.currentProperty?.business_date"
					class="rounded-full border border-secondary/20 bg-secondary-container px-2.5 py-1 text-[11px] font-semibold text-on-secondary-container"
					title="Business date: the hotel day in progress until night audit closes it"
				>
					{{ formatNight(hotel.currentProperty.business_date) }}
				</span>
			</div>

			<RouterLink
				v-if="newAction"
				:to="newAction.to"
				class="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-primary-dark focus-visible:ring-2 focus-visible:ring-secondary"
			>
				<span class="material-symbols-outlined text-[18px]">add</span>
				{{ newAction.label }}
			</RouterLink>

			<div class="hidden sm:flex flex-col items-end leading-tight pr-1">
				<span class="text-sm font-semibold text-text-main-light">
					{{ displayName }}
				</span>
				<span class="text-[12px] text-text-sub-light">
					{{ userDesignation }}
				</span>
			</div>

			<img
				class="h-11 w-11 rounded-full object-cover bg-surface-container ring-2 ring-secondary/40"
				:src="auth.userImage || defaultAvatar"
				alt="profile"
			/>
		</div>
	</header>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useHotelStore } from "@/stores/hotel.store";
import { HOTEL, SERVICES, useWorkspaceStore } from "@/stores/workspace.store";
import { formatNight } from "@/utils/hotelFormat";
import defaultAvatar from "@/assets/images/profile-circle.svg";

const auth = useAuthStore();
const hotel = useHotelStore();
const workspace = useWorkspaceStore();
const route = useRoute();

const pageMeta = {
	Dashboard: {
		sectionLabel: "Overview",
		title: "Today",
		description: "Track activity, performance, and today’s workload.",
		tag: "Live",
	},
	Services: {
		sectionLabel: "Booking flow",
		title: "Services",
		description: "Browse services, filter cards, and build bookings quickly.",
		tag: "Catalog",
	},
	NewBooking: {
		sectionLabel: "Booking flow",
		title: "New Appointment",
		description: "Pick services and move through guest assignment and checkout.",
		tag: "Draft",
	},
	GuestAssignment: {
		sectionLabel: "Booking flow",
		title: "Guest Assignment",
		description: "Confirm the guest details before checkout.",
		tag: "Step 2",
	},
	Checkout: {
		sectionLabel: "Booking flow",
		title: "Checkout",
		description: "Review services, totals, and payment details.",
		tag: "Payment",
	},
	Bookings: {
		sectionLabel: "Records",
		title: "Appointments",
		description: "Review appointment bookings and manage their status.",
		tag: "List",
	},
	BookingDetails: {
		sectionLabel: "Records",
		title: "Booking Details",
		description: "Inspect booking history, services, and actions.",
		tag: "Detail",
	},
	AppointmentDetails: {
		sectionLabel: "Records",
		title: "Appointment Details",
		description: "View appointment context and related actions.",
		tag: "Detail",
	},
	FrontDeskToday: {
		sectionLabel: "Hotel",
		title: "Front Desk",
		description: "Today's arrivals, in-house guests and departures.",
		tag: "Today",
	},
	HotelStay: {
		sectionLabel: "Hotel",
		title: "Reservation",
		description: "One stay: guests, room, prices and history.",
		tag: "Detail",
	},
	HotelBookings: {
		sectionLabel: "Hotel",
		title: "Reservations",
		description: "The latest hotel bookings at this property.",
		tag: "List",
	},
	HotelBooking: {
		sectionLabel: "Hotel",
		title: "Reservations",
		description: "The latest hotel bookings at this property.",
		tag: "List",
	},
	NewReservation: {
		sectionLabel: "Hotel",
		title: "New Reservation",
		description: "Search rooms and rates, choose the guest, and hold.",
		tag: "Draft",
	},
	Forbidden: {
		sectionLabel: "Access",
		title: "Forbidden",
		description: "You do not have permission to view this area.",
		tag: "Restricted",
	},
};

const currentPage = computed(() => pageMeta[route.name] || {});
const sectionLabel = computed(() => currentPage.value.sectionLabel || "Booking desk");
const pageTitle = computed(() => currentPage.value.title || "BookingDesk");
const pageDescription = computed(
	() => currentPage.value.description || "Manage bookings, services, and operations."
);
const pageTag = computed(() => currentPage.value.tag || "");

const displayName = computed(() => auth.userName || auth.userId || "Guest User");
const userDesignation = computed(() => {
	if (!auth.isLoggedIn) return "Guest";
	return workspace.active === HOTEL ? "Front Desk" : "Appointment Desk";
});

const propertyName = computed({
	get: () => hotel.property,
	set: (value) => hotel.setProperty(value),
});

// "New" follows the workspace: appointments in Services, reservations in Hotel (if the user books).
const newAction = computed(() => {
	if (workspace.active === HOTEL) {
		return hotel.canBook ? { label: "New Reservation", to: { name: "NewReservation" } } : null;
	}
	if (workspace.active === SERVICES) {
		return { label: "New Appointment", to: { name: "NewBooking" } };
	}
	return null;
});
</script>
