<template>
	<header
		class="h-16 bg-surface-light dark:bg-surface-dark border-b border-border-light dark:border-border-dark flex items-center justify-between px-6 shrink-0 z-20"
	>
		<RouterLink
			:to="{ name: 'Bookings' }"
			class="flex items-center gap-3 group cursor-pointer"
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
				<h1 class="text-xl font-extrabold leading-tight tracking-tight text-primary">
					Booking<span class="text-text-main-light dark:text-text-main-dark font-medium">
						Desk</span
					>
				</h1>
			</div>
		</RouterLink>
		<Search />
		<div class="hidden md:flex gap-4 relative z-[60]">
			<RouterLink
				class="bg-primary/20 px-4 lg:px-6 py-2 rounded-lg text-primary font-medium hover:bg-primary/30 transition-colors"
				v-if="!auth.isLoggedIn"
				:to="{ name: 'Login' }"
				>Log In</RouterLink
			>
			<Dropdown v-else :options="userMenuOptions" placement="bottom-end">
				<template v-slot="{ open }">
					<button
						class="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
					>
						<img
							class="h-10 w-10 lg:h-12 lg:w-12 rounded-full object-cover bg-gray-100"
							:src="auth.userImage || defaultAvatar"
							alt="profile"
						/>
					</button>
				</template>
			</Dropdown>
		</div>
	</header>
</template>

<script setup>
import { Dropdown } from "frappe-ui";
import { useAuthStore } from "@/stores/auth";
import { ref, computed } from "vue";
import { useRouter } from "vue-router";

import Search from "./Search.vue";
import defaultAvatar from "@/assets/images/profile-circle.svg";

const auth = useAuthStore();
const router = useRouter();
const mobileMenuOpen = ref(false);

const userMenuOptions = computed(() => [
	{
		label: "User Profile",
		icon: "user",
		onClick: () => {
			router.push({ name: "User" });
		},
	},
	{
		label: "Logout",
		icon: "log-out",
		onClick: handleLogout,
	},
]);

async function handleLogout() {
	mobileMenuOpen.value = false;
	await auth.logout();
	window.location.reload();
}
</script>
