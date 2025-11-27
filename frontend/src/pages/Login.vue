<template>
	<div class="my-14 flex flex-row items-center justify-center bg-white">
		<Card
			title="Login to your FrappeUI App!"
			class="w-full max-w-md mt-4 bg-blue-300 p-4 rounded"
		>
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
				<Button :loading="session.login.loading" variant="solid">Login</Button>
			</form>
		</Card>
	</div>
</template>

<script lang="ts" setup>
import { createResource } from "frappe-ui";
import { sessionStore } from "../data/session";
import Card from "frappe-ui/src/components/Card.vue";
import { computed, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const userEmail = ref("");
const password = ref("");
const signInState = ref(false);
const signUpForm = reactive({
	first_name: String,
	last_name: String,
	email: String,
	gender: String,
	phone: String,
});

const session = sessionStore();

const isLogin = computed(() => route.hash !== "#signup");

function toggleForm() {
	isLogin.value ? router.replace({ hash: "#signup" }) : router.replace({ hash: "#login" });
}

function resetSignUpForm(form) {
	form.first_name = "";
	form.last_name = "";
	form.email = "";
	form.gender = "";
	form.phone = "";
}

const createSignup = createResource({
	url: "frappoint.frappoint.api.user.create_user",
	onSuccess() {
		signInState.value = true;
		resetSignUpForm(signUpForm);
		router.replace({ hash: "#login" });
	},
});

function submit() {
	if (isLogin.value) {
		session.login.submit(
			{ usr: userEmail, pwd: password.value },
			{
				onSuccess: () => {
					const redirectTo = route.query.redirectTo;

					if (redirectTo) {
						// Convert to string if it's an array, take first value
						const destination = Array.isArray(redirectTo) ? redirectTo[0] : redirectTo;
						router.push(destination || "/");
					} else {
						router.push("/");
					}
				},
			}
		);
	} else {
		createSignup.submit({
			...signUpForm,
		});
	}
}
</script>
