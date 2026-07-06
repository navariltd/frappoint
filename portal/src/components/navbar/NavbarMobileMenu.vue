<template>
	<Transition
		enter-active-class="transition-all duration-200 ease-out"
		enter-from-class="opacity-0 -translate-y-2"
		enter-to-class="opacity-100 translate-y-0"
		leave-active-class="transition-all duration-150 ease-in"
		leave-from-class="opacity-100 translate-y-0"
		leave-to-class="opacity-0 -translate-y-2"
	>
		<div v-if="open" class="md:hidden border-t border-outline-variant/30 bg-surface shadow-lg">
			<div class="px-4 py-3 space-y-3">
				<RouterLink
					class="block py-2 text-on-surface-variant hover:text-primary transition-colors font-medium"
					active-class="!text-primary font-bold"
					:to="{ name: 'Services' }"
					@click="$emit('close')"
				>
					Discovery
				</RouterLink>
				<RouterLink
					class="block py-2 text-on-surface-variant hover:text-primary transition-colors font-medium"
					active-class="!text-primary font-bold"
					:to="{ name: 'Bookings' }"
					@click="$emit('close')"
				>
					My Bookings
				</RouterLink>
				<div class="pt-3 border-t border-outline-variant/30">
					<RouterLink
						v-if="!isLoggedIn"
						class="block bg-primary/20 px-4 py-2 rounded-lg text-primary font-medium text-center hover:bg-primary/30 transition-colors"
						:to="{ name: 'Login' }"
						@click="$emit('close')"
					>
						Log In
					</RouterLink>
					<div v-else class="space-y-2">
						<div class="flex items-center gap-3 py-2 px-2">
							<img
								class="h-10 w-10 rounded-full object-cover"
								:src="userImage || defaultAvatar"
								alt="profile"
							/>
							<p class="text-on-surface font-medium">{{ userName }}</p>
						</div>
						<RouterLink
							:to="{ name: 'User' }"
							class="block py-2 px-2 text-on-surface-variant hover:text-primary transition-colors font-medium"
							@click="$emit('close')"
						>
							User Profile
						</RouterLink>
						<button
							class="block w-full text-left py-2 px-2 text-error hover:opacity-90 transition-colors font-medium"
							@click="$emit('logout')"
						>
							Logout
						</button>
					</div>
				</div>
			</div>
		</div>
	</Transition>
</template>

<script setup>
import defaultAvatar from "@/assets/images/profile-circle.svg";

defineProps({
	open: { type: Boolean, default: false },
	isLoggedIn: { type: Boolean, default: false },
	userName: { type: String, default: "" },
	userImage: { type: String, default: "" },
});

defineEmits(["close", "logout"]);
</script>
