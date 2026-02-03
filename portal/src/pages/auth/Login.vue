<template>
	<div
		class="flex min-h-screen items-start justify-center pt-12 pb-6 px-6 bg-[#f6f8f8] dark:bg-[#141e1e] font-sans overflow-y-auto scrollbar-hide"
	>
		<div
			class="w-full max-w-[440px] bg-white dark:bg-[#1c2a2a] rounded-xl shadow-[0_10px_25px_-5px_rgba(0,0,0,0.05),0_8px_10px_-6px_rgba(0,0,0,0.05)] p-8 md:p-10 border border-[#eaf0f0] dark:border-gray-800"
		>
			<div class="text-center mb-8">
				<div
					class="inline-flex items-center justify-center size-12 rounded-full bg-[#2c7677]/10 text-[#2c7677] mb-4"
				>
					<span class="material-symbols-outlined" style="font-size: 28px"
						>lock_open</span
					>
				</div>
				<h1 class="text-[#111818] dark:text-white text-2xl font-bold tracking-tight mb-2">
					Welcome back
				</h1>
				<p class="text-[#5e8787] text-sm">Sign in to manage your bookings and schedule</p>
			</div>

			<form class="space-y-5" @submit.prevent="submit">
				<div class="flex flex-col gap-2">
					<label
						for="email"
						class="text-[#111818] dark:text-gray-200 text-sm font-semibold"
					>
						Email Address
					</label>
					<input
						id="email"
						v-model="email"
						required
						type="email"
						class="w-full rounded-xl text-[#111818] dark:text-white border border-[#d5e2e2] dark:border-gray-700 bg-white dark:bg-background-dark focus:border-[#2c7677] focus:ring-1 focus:ring-[#2c7677] h-12 px-4 text-sm font-normal placeholder:text-[#8B949E] transition-colors"
						placeholder="name@company.com"
					/>
				</div>

				<div class="flex flex-col gap-2">
					<div class="flex justify-between items-center">
						<label
							for="password"
							class="text-[#111818] dark:text-gray-200 text-sm font-semibold"
						>
							Password
						</label>
						<a href="#" class="text-[#2c7677] text-xs font-bold hover:underline">
							Forgot password?
						</a>
					</div>
					<div class="relative flex items-center">
						<input
							id="password"
							v-model="password"
							required
							:type="showPassword ? 'text' : 'password'"
							class="w-full rounded-xl text-[#111818] dark:text-white border border-[#d5e2e2] dark:border-gray-700 bg-white dark:bg-background-dark focus:border-[#2c7677] focus:ring-1 focus:ring-[#2c7677] h-12 px-4 text-sm font-normal placeholder:text-[#8B949E] transition-colors pr-10"
							placeholder="••••••••"
						/>
						<button
							type="button"
							class="absolute right-3 text-[#5e8787] flex items-center hover:text-[#2c7677] transition-colors select-none outline-none focus:outline-none"
							@click="showPassword = !showPassword"
						>
							<span class="material-symbols-outlined" style="font-size: 20px">
								{{ showPassword ? "visibility_off" : "visibility" }}
							</span>
						</button>
					</div>
				</div>

				<div class="flex items-center gap-2">
					<input
						id="remember"
						v-model="rememberMe"
						type="checkbox"
						class="size-4 rounded border-[#d5e2e2] text-[#2c7677] focus:ring-[#2c7677]"
					/>
					<label for="remember" class="text-xs text-[#5e8787] font-medium select-none">
						Keep me signed in
					</label>
				</div>

				<!-- Error Message -->
				<div
					v-if="errorMessage"
					class="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
				>
					<span
						class="material-symbols-outlined text-red-600 dark:text-red-400 text-[20px]"
					>
						error
					</span>
					<p class="text-sm text-red-600 dark:text-red-400 font-medium">
						{{ errorMessage }}
					</p>
				</div>

				<button
					type="submit"
					:disabled="auth.loading"
					class="w-full flex items-center justify-center rounded-xl h-12 bg-[#2c7677] text-white text-sm font-bold shadow-lg shadow-[#2c7677]/20 hover:brightness-110 active:scale-[0.98] transition-all disabled:opacity-70 disabled:cursor-not-allowed"
				>
					<svg
						v-if="auth.loading"
						class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
					>
						<circle
							class="opacity-25"
							cx="12"
							cy="12"
							r="10"
							stroke="currentColor"
							stroke-width="4"
						></circle>
						<path
							class="opacity-75"
							fill="currentColor"
							d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
						></path>
					</svg>
					<span v-if="!auth.loading">Sign In</span>
					<span v-else>Signing in...</span>
				</button>
			</form>

			<div class="mt-6 text-center">
				<p class="text-sm text-[#5e8787]">
					Don't have an account?
					<RouterLink
						:to="{ name: 'Signup', query: { redirect: route.query.redirect } }"
						class="text-[#2c7677] font-bold hover:underline"
					>
						Sign up
					</RouterLink>
				</p>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { ref } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useRoute, useRouter } from "vue-router";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

// Reactive state for form inputs
const email = ref("");
const password = ref("");
const rememberMe = ref(false);
const showPassword = ref(false);
const errorMessage = ref("");

async function submit() {
	// Clear any previous error
	errorMessage.value = "";

	try {
		// We now use the reactive variables instead of FormData
		await auth.login(email.value, password.value);

		// Optional: handle "rememberMe" logic here if your backend supports it
		// console.log('Remember me:', rememberMe.value);

		const redirect = (route.query.redirect as string) || "/";
		router.replace(redirect);
	} catch (error) {
		// Display error message
		errorMessage.value = "Invalid Credentials";

		// Reset form
		password.value = "";
		showPassword.value = false;
	}
}
</script>

<style scoped>
/*
  Ensure your project has the '@tailwindcss/forms' plugin enabled
  in tailwind.config.js for the default checkbox styling to work correctly.
*/
</style>
