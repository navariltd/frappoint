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
				</template>
				<template v-else>
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
						<Input
							required
							name="firstname"
							type="text"
							:placeholder="'John'"
							:label="'First Name'"
							v-model="signUpForm.first_name"
						/>
						<Input
							required
							name="lastname"
							type="text"
							placeholder="Doe"
							label="Last Name"
							v-model="signUpForm.last_name"
						/>
					</div>
					<Input
						required
						name="email"
						type="text"
						placeholder="johndoe@email.com"
						label="Email"
						v-model="signUpForm.email"
					/>
					<Input
						required
						name="phone"
						type="text"
						placeholder="0712345678"
						label="Phone Number"
						v-model="signUpForm.phone"
					/>
					<ErrorMessage v-if="phoneNumberError" :message="phoneNumberError" />
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
					<div class="flex items-center space-x-2">
						<Input
							required
							name="confirmPassword"
							:type="isPwdVisible ? 'text' : 'password'"
							placeholder="••••••"
							label="Confirm Password"
							class="w-full"
							v-model="confirmPassword"
						/>
					</div>
					<ErrorMessage v-if="passwordError" :message="passwordError" />
				</template>
				<Button
					:loading="isLogin ? session.login.loading : createSignUp.loading"
					variant="solid"
					type="submit"
					theme="blue"
					class="font-semibold"
				>
					{{ isLogin ? "Login" : "Register" }}
				</Button>
			</form>

			<div class="mt-2 text-center">
				<ErrorMessage v-if="isLogin" :message="session.login.error" />
				<ErrorMessage v-else :message="signUpError || createSignUp.error" />
			</div>
			<div class="flex mt-4 text-center justify-center text-sm gap-1">
				<span v-if="isLogin">{{ "Don’t have an account?" }} </span>
				<span v-else>{{ "Already have an account?" }} </span>
				<button
					class="text-blue-500 hover:underline font-medium"
					@click="toggleForm"
					type="button"
				>
					{{ isLogin ? "Sign up" : "Login" }}
				</button>
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
import {
	initialForm,
	resetSignUpForm,
	validatePasswordMatch,
	validatePhoneNumber,
} from "../utils/user";

const route = useRoute();
const router = useRouter();

const userEmail = ref("");
const password = ref("");
const confirmPassword = ref("");
const isPwdVisible = ref(false);
const signInState = ref(false);
const signUpForm = reactive({ ...initialForm });

const passwordError = ref("");
const phoneNumberError = ref("");
const signUpError = ref("");

const session = sessionStore();

const isLogin = computed(() => route.hash !== "#signup");

function toggleForm() {
	passwordError.value = "";
	signUpError.value = "";
	password.value = "";
	confirmPassword.value = "";
	userEmail.value = "";

	resetSignUpForm(signUpForm);

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
	passwordError.value = "";
	signUpError.value = "";
	phoneNumberError.value = "";

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
		try {
			validatePasswordMatch(password.value, confirmPassword.value);
			validatePhoneNumber(signUpForm.phone);
		} catch (error: any) {
			if (error.message.toLowerCase().includes("password")) {
				passwordError.value = error.message;
			} else {
				phoneNumberError.value = error.message;
			}
			return;
		}
		createSignUp.submit(
			{
				...signUpForm,
			},
			{
				onError: (error: any) => {
					signUpError.value = error.message || "Registration failed, please try again";
				},
			}
		);
	}
}
</script>
