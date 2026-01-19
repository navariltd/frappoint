<template>
	<div
		class="w-full sticky top-0 z-50 bg-surface-light/90 backdrop-blur-md border-b border-gray-200 transition-colors duration-300"
	>
		<div class="w-full max-w-7xl mx-auto flex justify-between items-center py-4 px-6">
			<RouterLink :to="{ name: 'Services' }">
				<div class="flex items-center gap-3">
					<img class="h-8 w-8" src="@/assets/images/logo_img.png" alt="logo" />
					<h1 class="text-xl font-bold tracking-tight text-gray-900">Frappoint</h1>
				</div>
			</RouterLink>

			<div class="flex gap-4">
				<RouterLink :to="{ name: 'Services' }"> Services </RouterLink>
				<RouterLink :to="{ name: 'Bookings' }"> My Bookings </RouterLink>
			</div>

			<div class="flex gap-4">
				<RouterLink
					class="bg-primary/20 px-6 py-2 rounded-lg text-primary font-medium"
					v-if="!auth.isLoggedIn"
					:to="{ name: 'Login' }"
					>Log In</RouterLink
				>
				<RouterLink :to="{ name: 'User', params: { name: auth.userId } }" v-else>
					<div class="flex items-center">
						<div>
							<p>{{ auth.userName }}</p>
						</div>
						<div class="ps-4">
							<img
								class="h-14 w-14 rounded-full object-cover"
								v-if="auth.userImage"
								:src="auth.userImage"
								alt="profile"
							/>
							<FeatherIcon v-else class="h-8" name="user" size="24px" />
						</div>
					</div>
				</RouterLink>
			</div>
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
</script>
