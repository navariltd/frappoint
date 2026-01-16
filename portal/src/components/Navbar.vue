<template>
	<div class="bg-white/80 w-full">
		<div class="w-full max-w-7xl mx-auto flex justify-between items-center py-4 px-6">
			<RouterLink>
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
				<RouterLink>
					<FeatherIcon class="h-8" name="bell" />
				</RouterLink>
				<RouterLink>
					<div class="flex">
						<div>
							<p>John Doe</p>
							<p>Member</p>
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
import { ref } from "vue";

const userProfile = ref(false);
</script>
