<template>
	<div class="my-14 flex flex-row items-center justify-center bg-white">
		<Card
			:title="isLogin ? 'Login to Frappoint' : 'Sign Up'"
			:class="isLogin ? 'w-full max-w-md' : 'w-full max-w-2xl'"
		>
			<form class="flex flex-col space-y-4 w-full" @submit.prevent="submit">
				<template v-if="isLogin">
					<Input
						required
						name="email"
						type="text"
						placeholder="johndoe@email.com"
						label="Email/User ID"
						v-model="userEmail"
					/>
					<div class="flex items-center space-x-2">
						<Input
							required
							name="password"
							:type="isPwdVisible ? 'text' : 'password'"
							placeholder="••••••"
							label="Password"
							class="w-full"
							v-model="password"
						/>
						<Eye
							v-if="!isPwdVisible"
							class="w-5 h-5 mt-6 cursor-pointer text-gray-600"
							@click="isPwdVisible = !isPwdVisible"
						/>
						<EyeOff
							v-if="isPwdVisible"
							class="w-5 h-5 mt-6 cursor-pointer text-gray-600"
							@click="isPwdVisible = !isPwdVisible"
						/>
					</div>
					<Button
						:loading="isLogin ? session.login.loading : createSignUp.loading"
						variant="solid"
						type="submit"
						theme="blue"
						>Login</Button
					>
				</template>
			</form>

			<div class="mt-2 text-center">
				<ErrorMessage :message="isLogin ? session.login.error : createSignUp.error" />
			</div>
		</Card>
	</div>
</template>

<script lang="ts" setup>
import { createResource } from "frappe-ui";
import { sessionStore } from "../data/session";
import Button from "frappe-ui/src/components/Button/Button.vue";
import Card from "frappe-ui/src/components/Card.vue";
import Input from "frappe-ui/src/components/Input.vue";
import ErrorMessage from "frappe-ui/src/components/ErrorMessage/ErrorMessage.vue";
import { computed, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Eye, EyeOff } from "lucide-vue-next";
import { initialForm, resetSignUpForm } from "../utils/user";

const route = useRoute();
const router = useRouter();

const userEmail = ref("");
const password = ref("");
const isPwdVisible = ref(false);
const signInState = ref(false);
const signUpForm = reactive({ ...initialForm });

const session = sessionStore();

const isLogin = computed(() => route.hash !== "#signup");

function toggleForm() {
	isLogin.value ? router.replace({ hash: "#signup" }) : router.replace({ hash: "#login" });
}

const createSignUp = createResource({
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
			{ usr: userEmail.value, pwd: password.value },
			{
				onSuccess: () => {
					const redirectTo = route.query.redirectTo;

					if (redirectTo) {
						const destination = Array.isArray(redirectTo) ? redirectTo[0] : redirectTo;
						router.push(destination || "/");
					} else {
						router.push("/");
					}
				},
			}
		);
	} else {
		createSignUp.submit({
			...signUpForm,
		});
	}
}
</script>
