<template>
	<div class="m-3 flex flex-row items-center justify-center">
		<Card title="Login to your FrappeUI App!" class="w-full max-w-md mt-4">
			<form class="flex flex-col space-y-2 w-full" @submit.prevent="submit">
				<Input
					required
					name="email"
					type="text"
					placeholder="johndoe@email.com"
					label="User ID"
				/>
				<Input
					required
					name="password"
					type="password"
					placeholder="••••••"
					label="Password"
				/>
				<Button type="submit" :loading="auth.loading" variant="solid">Login</Button>
			</form>
		</Card>
	</div>
</template>

<script lang="ts" setup>
import { Card, Input, Button } from "frappe-ui";
import { useAuthStore } from "@/stores/auth";
import { useRoute, useRouter } from "vue-router";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

async function submit(e) {
	const formData = new FormData(e.target);
	await auth.login(formData.get("email"), formData.get("password"));

	const redirect = route.query.redirect || "/";
	router.replace(redirect);
}
</script>
