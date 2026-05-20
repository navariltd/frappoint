<template>
	<div
		class="bg-surface/90 dark:bg-surface-dim/90 backdrop-blur-md border-b border-outline-variant/30 shadow-sm docked full-width top-0 sticky z-50"
	>
		<div class="max-w-7xl mx-auto px-gutter h-20 w-full flex items-center justify-between">
			<NavbarLogo />

			<NavbarLinks :isLoggedIn="auth.isLoggedIn" />

			<div class="flex items-center gap-3">
				<NavbarCartIndicator :count="appointmentBasketCount" @open="goToBookings" />
				<NavbarUserMenu
					:isLoggedIn="auth.isLoggedIn"
					:userImage="auth.userImage"
					@logout="handleLogout"
				/>
				<button
					type="button"
					class="md:hidden p-2 text-on-surface-variant hover:text-primary transition-colors flex items-center justify-center"
					aria-label="Toggle menu"
					@click="mobileMenuOpen = !mobileMenuOpen"
				>
					<MenuIcon v-if="!mobileMenuOpen" />
					<CloseIcon v-else />
				</button>
			</div>
		</div>
		<NavbarMobileMenu
			:open="mobileMenuOpen"
			:isLoggedIn="auth.isLoggedIn"
			:userName="auth.userName"
			:userImage="auth.userImage"
			@close="mobileMenuOpen = false"
			@logout="handleLogout"
		/>
	</div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useBookingStore } from "@/stores/bookingStore";
import { useRouter } from "vue-router";
import NavbarLogo from "@/components/navbar/NavbarLogo.vue";
import NavbarLinks from "@/components/navbar/NavbarLinks.vue";
import NavbarCartIndicator from "@/components/navbar/NavbarCartIndicator.vue";
import NavbarUserMenu from "@/components/navbar/NavbarUserMenu.vue";
import NavbarMobileMenu from "@/components/navbar/NavbarMobileMenu.vue";
import MenuIcon from "@/components/icons/MenuIcon.vue";
import CloseIcon from "@/components/icons/CloseIcon.vue";

const auth = useAuthStore();
const bookingStore = useBookingStore();
const router = useRouter();
const mobileMenuOpen = ref(false);

const appointmentBasketCount = computed(() => bookingStore.draft.appointments?.length || 0);

function goToBookings() {
	mobileMenuOpen.value = false;
	router.push({ name: "Bookings" });
}

async function handleLogout() {
	mobileMenuOpen.value = false;
	await auth.logout();
}

onMounted(() => {
	auth.refreshUser();
});
</script>
