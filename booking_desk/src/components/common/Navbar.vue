<template>
	<nav
		class="fixed inset-y-0 left-0 z-50 w-64 bg-surface-light border-r border-gray-200 flex flex-col transition-transform duration-300 md:translate-x-0"
		:class="mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'"
	>
		<div class="h-16 flex items-center px-6 border-b border-gray-100">
			<RouterLink :to="{ name: 'Bookings' }" class="flex items-center gap-3">
				<img class="h-8 w-8" src="@/assets/images/logo_img.png" alt="logo" />
				<h1 class="text-xl font-bold tracking-tight text-gray-900">Frappoint</h1>
			</RouterLink>
		</div>

		<div class="flex-1 overflow-y-auto py-6 px-4 space-y-2">
			<RouterLink
				class="flex items-center gap-3 px-4 py-2.5 rounded-lg text-gray-700 hover:bg-primary/10 hover:text-primary transition-all font-medium"
				active-class="bg-primary/10 !text-primary font-bold"
				:to="{ name: 'Bookings' }"
			>
				Appointments
			</RouterLink>
			<RouterLink
				class="flex items-center gap-3 px-4 py-2.5 rounded-lg text-gray-700 hover:bg-primary/10 hover:text-primary transition-all font-medium"
				active-class="bg-primary/10 !text-primary font-bold"
				:to="{ name: 'Services' }"
			>
				Services
			</RouterLink>
		</div>

		<div class="p-4 border-t border-gray-200 bg-gray-50/50">
			<div v-if="!auth.isLoggedIn">
				<RouterLink
					class="block w-full text-center bg-primary px-4 py-2.5 rounded-lg text-white font-medium hover:bg-primary-dark transition-colors"
					:to="{ name: 'Login' }"
				>
					Log In
				</RouterLink>
			</div>

			<Dropdown v-else :options="userMenuOptions" placement="top-start" class="w-full">
				<template v-slot="{ open }">
					<button
						class="w-full flex items-center gap-3 p-2 rounded-xl hover:bg-white hover:shadow-sm border border-transparent hover:border-gray-200 transition-all text-left"
					>
						<img
							class="h-10 w-10 rounded-full object-cover bg-gray-200"
							:src="auth.userImage || defaultAvatar"
							alt="profile"
						/>
						<div class="flex-1 min-w-0">
							<p class="text-sm font-semibold text-gray-900 truncate">
								{{ auth.userName || "User" }}
							</p>
							<p class="text-xs text-gray-500 truncate">View Profile</p>
						</div>
					</button>
				</template>
			</Dropdown>
		</div>
	</nav>

	<div
		class="md:hidden flex items-center justify-between p-4 bg-white border-b sticky top-0 z-40"
	>
		<img class="h-7 w-7" src="@/assets/images/logo_img.png" alt="logo" />
		<button @click="mobileMenuOpen = !mobileMenuOpen" class="p-2 text-gray-600">
			<MenuIcon v-if="!mobileMenuOpen" />
			<CloseIcon v-else />
		</button>
	</div>

	<div
		v-if="mobileMenuOpen"
		@click="mobileMenuOpen = false"
		class="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 md:hidden"
	></div>
</template>

<script setup>
import { Dropdown } from "frappe-ui";
import { useAuthStore } from "@/stores/auth";
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import MenuIcon from "@/components/icons/MenuIcon.vue";
import CloseIcon from "@/components/icons/CloseIcon.vue";
import defaultAvatar from "@/assets/images/profile-circle.svg";

const auth = useAuthStore();
const router = useRouter();
const mobileMenuOpen = ref(false);

const userMenuOptions = computed(() => [
	{
		label: "User Profile",
		icon: "user",
		onClick: () => {
			console.log("User Profile Menu Option Clicked");
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
