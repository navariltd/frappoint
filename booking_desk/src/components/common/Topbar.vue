<template>
	<header
		class="h-20 bg-surface-light/95 dark:bg-surface-dark/95 backdrop-blur border-b border-border-light/80 dark:border-border-dark/80 flex items-center justify-between px-6 shrink-0 z-20"
	>
		<div class="min-w-0 flex-1 pr-4">
			<p
				class="text-[11px] font-semibold uppercase tracking-[0.18em] text-text-sub-light dark:text-text-sub-dark"
			>
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
					class="shrink-0 rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary"
				>
					{{ pageTag }}
				</span>
			</div>
			<p class="mt-1 truncate text-[12px] text-text-sub-light dark:text-text-sub-dark">
				{{ pageDescription }}
			</p>
		</div>
		<div class="flex items-center gap-3 md:gap-4 pl-4 shrink-0">
			<RouterLink
				:to="{ name: 'NewBooking' }"
				class="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-primary/90"
			>
				<span class="material-symbols-outlined text-[18px]">add</span>
				New Booking
			</RouterLink>

			<div class="hidden sm:flex flex-col items-end leading-tight pr-1">
				<span class="text-sm font-semibold text-text-main-light dark:text-text-main-dark">
					{{ displayName }}
				</span>
				<span class="text-[12px] text-text-sub-light dark:text-text-sub-dark">
					{{ userDesignation }}
				</span>
			</div>

			<img
				class="h-11 w-11 rounded-full object-cover bg-gray-100 ring-2 ring-white dark:ring-gray-800"
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
import defaultAvatar from "@/assets/images/profile-circle.svg";

const auth = useAuthStore();
const route = useRoute();

const pageMeta = {
	Dashboard: {
		sectionLabel: "Overview",
		title: "Dashboard",
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
		title: "New Booking",
		description: "Start a draft booking and move through guest assignment.",
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
		title: "Bookings",
		description: "Review existing bookings and manage their status.",
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
const userDesignation = computed(() => (auth.isLoggedIn ? "Appointment Desk" : "Guest"));
</script>
