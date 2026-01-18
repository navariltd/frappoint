<template>
	<div class="bg-white/80 w-full">
		<div class="w-full max-w-7xl mx-auto flex justify-between items-center py-4 px-6">
			<RouterLink :to="{ name: 'Services' }">
				<div class="flex gap-3">
					<img src="" alt="logo" />
					<h1>Frappoint</h1>
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
				<RouterLink v-else>
					<div class="flex items-center">
						<div>
							<p>{{ auth.userName }}</p>
						</div>
						<div class="ps-4">
							<img v-if="userProfile" src="" alt="profile" />
							<FeatherIcon class="h-8" name="user" size="24px" />
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
