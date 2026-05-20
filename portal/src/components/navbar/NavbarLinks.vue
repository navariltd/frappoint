<template>
	<nav class="hidden md:flex items-center gap-stack-md">
		<RouterLink
			class="font-body-md text-body-md text-on-surface-variant font-medium hover:text-primary transition-colors"
			active-class="text-primary font-bold border-b-2 border-primary pb-1"
			:to="{ name: 'Services' }"
		>
			Discovery
		</RouterLink>
		<RouterLink
			class="font-body-md text-body-md text-on-surface-variant font-medium hover:text-primary transition-colors"
			active-class="text-primary font-bold border-b-2 border-primary pb-1"
			:to="{ name: 'Bookings' }"
		>
			My Bookings
		</RouterLink>
		<RouterLink
			v-if="isLoggedIn"
			class="font-body-md text-body-md text-on-surface-variant font-medium hover:text-primary transition-colors"
			active-class="text-primary font-bold border-b-2 border-primary pb-1"
			:to="{ name: 'User' }"
		>
			Profile
		</RouterLink>
	</nav>
</template>

<script setup>
defineProps({
	isLoggedIn: { type: Boolean, default: false },
});
</script>
