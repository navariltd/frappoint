<template>
	<div
		class="w-full sticky top-0 z-50 bg-surface-light/90 backdrop-blur-md border-b border-gray-200 transition-colors duration-300"
	>
		<div
			class="w-full max-w-7xl mx-auto flex justify-between items-center py-3 md:py-4 px-4 md:px-6"
		>
			<!-- Logo -->
			<RouterLink :to="{ name: 'Services' }">
				<div class="flex items-center gap-2 md:gap-3">
					<img
						class="h-7 w-7 md:h-8 md:w-8"
						src="@/assets/images/logo_img.png"
						alt="logo"
					/>
					<h1 class="text-lg md:text-xl font-bold tracking-tight text-gray-900">
						Frappoint
					</h1>
				</div>
			</RouterLink>

			<!-- Desktop Navigation -->
			<div class="hidden md:flex gap-4 lg:gap-6">
				<RouterLink
					class="text-gray-700 hover:text-primary transition-colors font-medium"
					:to="{ name: 'Services' }"
				>
					Services
				</RouterLink>
				<RouterLink
					class="text-gray-700 hover:text-primary transition-colors font-medium"
					:to="{ name: 'Bookings' }"
				>
					My Bookings
				</RouterLink>
			</div>

			<!-- Desktop User Section -->
			<div class="hidden md:flex gap-4">
				<RouterLink
					class="bg-primary/20 px-4 lg:px-6 py-2 rounded-lg text-primary font-medium hover:bg-primary/30 transition-colors"
					v-if="!auth.isLoggedIn"
					:to="{ name: 'Login' }"
					>Log In</RouterLink
				>
				<RouterLink :to="{ name: 'User', params: { name: auth.userId } }" v-else>
					<div class="flex items-center gap-2">
						<p class="hidden lg:block text-gray-700">{{ auth.userName }}</p>
						<img
							class="h-10 w-10 lg:h-12 lg:w-12 rounded-full object-cover"
							v-if="auth.userImage"
							:src="auth.userImage"
							alt="profile"
						/>
						<FeatherIcon v-else class="h-10 w-10" name="user" />
					</div>
				</RouterLink>
			</div>

			<!-- Mobile Menu Button -->
			<button
				@click="mobileMenuOpen = !mobileMenuOpen"
				class="md:hidden p-2 text-gray-700 hover:text-primary transition-colors flex items-center justify-center"
				aria-label="Toggle menu"
			>
				<MenuIcon v-if="!mobileMenuOpen" />
				<CloseIcon v-else />
			</button>
		</div>

		<!-- Mobile Menu -->
		<Transition
			enter-active-class="transition-all duration-200 ease-out"
			enter-from-class="opacity-0 -translate-y-2"
			enter-to-class="opacity-100 translate-y-0"
			leave-active-class="transition-all duration-150 ease-in"
			leave-from-class="opacity-100 translate-y-0"
			leave-to-class="opacity-0 -translate-y-2"
		>
			<div
				v-if="mobileMenuOpen"
				class="md:hidden border-t border-gray-200 bg-white shadow-lg"
			>
				<div class="px-4 py-3 space-y-3">
					<RouterLink
						@click="mobileMenuOpen = false"
						class="block py-2 text-gray-700 hover:text-primary transition-colors font-medium"
						:to="{ name: 'Services' }"
					>
						Services
					</RouterLink>
					<RouterLink
						@click="mobileMenuOpen = false"
						class="block py-2 text-gray-700 hover:text-primary transition-colors font-medium"
						:to="{ name: 'Bookings' }"
					>
						My Bookings
					</RouterLink>
					<div class="pt-3 border-t border-gray-200">
						<RouterLink
							@click="mobileMenuOpen = false"
							class="block bg-primary/20 px-4 py-2 rounded-lg text-primary font-medium text-center hover:bg-primary/30 transition-colors"
							v-if="!auth.isLoggedIn"
							:to="{ name: 'Login' }"
						>
							Log In
						</RouterLink>
						<RouterLink
							@click="mobileMenuOpen = false"
							:to="{ name: 'User', params: { name: auth.userId } }"
							v-else
						>
							<div class="flex items-center gap-3 py-2">
								<img
									class="h-10 w-10 rounded-full object-cover"
									v-if="auth.userImage"
									:src="auth.userImage"
									alt="profile"
								/>
								<FeatherIcon v-else class="h-10 w-10" name="user" />
								<p class="text-gray-700 font-medium">{{ auth.userName }}</p>
							</div>
						</RouterLink>
					</div>
				</div>
			</div>
		</Transition>
	</div>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui";
import { useAuthStore } from "@/stores/auth";
import { ref } from "vue";
import MenuIcon from "@/components/icons/MenuIcon.vue";
import CloseIcon from "@/components/icons/CloseIcon.vue";

const auth = useAuthStore();
const mobileMenuOpen = ref(false);
</script>
