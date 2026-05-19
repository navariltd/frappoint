<template>
	<header
		class="h-20 bg-surface-light dark:bg-surface-dark border-b border-border-light dark:border-border-dark flex items-center justify-between px-6 shrink-0 z-20"
	>
		<div class="flex-1 max-w-3xl">
			<Search />
		</div>
		<div class="flex items-center gap-4 md:gap-6 pl-6">
			<RouterLink
				:to="{ name: 'NewBooking' }"
				class="px-6 py-2.5 bg-primary text-white font-semibold rounded-sm hover:bg-primary/90 transition-colors shadow-sm"
			>
				+ New Booking
			</RouterLink>

			<button
				type="button"
				class="relative inline-flex h-12 w-12 items-center justify-center rounded-full border border-border-light dark:border-border-dark bg-white dark:bg-gray-800 text-text-sub-light dark:text-text-sub-dark hover:text-primary transition-colors"
				aria-label="Notifications"
			>
				<span class="material-symbols-outlined text-[24px]">notifications</span>
				<span
					class="absolute top-2 right-2 h-2 w-2 rounded-full bg-red-500 ring-2 ring-white dark:ring-gray-800"
				></span>
			</button>

			<div class="hidden sm:flex flex-col items-end leading-tight">
				<span
					class="text-base font-semibold text-text-main-light dark:text-text-main-dark"
				>
					{{ displayName }}
				</span>
				<span class="text-sm text-text-sub-light dark:text-text-sub-dark">
					{{ userDesignation }}
				</span>
			</div>

			<img
				class="h-12 w-12 rounded-full object-cover bg-gray-100"
				:src="auth.userImage || defaultAvatar"
				alt="profile"
			/>
		</div>
	</header>
</template>

<script setup>
import { useAuthStore } from "@/stores/auth";
import { computed } from "vue";
import { RouterLink } from "vue-router";

import Search from "./Search.vue";
import defaultAvatar from "@/assets/images/profile-circle.svg";

const auth = useAuthStore();

const displayName = computed(() => auth.userName || auth.userId || "Guest User");
const userDesignation = computed(() => (auth.isLoggedIn ? "Appointment Desk" : "Guest"));
</script>
