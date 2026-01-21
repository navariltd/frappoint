<template>
	<div
		class="flex min-h-screen items-center justify-center p-6 bg-[#f6f8f8] dark:bg-[#141e1e] font-sans"
	>
		<div
			class="w-full max-w-[440px] bg-white dark:bg-[#1c2a2a] rounded-xl shadow-[0_10px_25px_-5px_rgba(0,0,0,0.05),0_8px_10px_-6px_rgba(0,0,0,0.05)] p-8 md:p-10 border border-[#eaf0f0] dark:border-gray-800"
		>
			<div class="text-center mb-8">
				<h1 class="text-[#111818] dark:text-white text-2xl font-bold tracking-tight mb-2">
					Create your account
				</h1>
				<p class="text-[#5e8787] text-sm">
					Join our booking platform to manage your services and grow your business today.
				</p>
			</div>

			<form class="space-y-5" @submit.prevent="submit">
				<!-- Full Name Field -->
				<div class="flex flex-col gap-2">
					<label
						for="fullName"
						class="text-[#111818] dark:text-gray-200 text-sm font-semibold"
					>
						Full Name
					</label>
					<div class="relative flex items-center">
						<span
							class="absolute left-3 text-[#5e8787] material-symbols-outlined"
							style="font-size: 20px"
						>
							person
						</span>
						<input
							id="fullName"
							v-model="fullName"
							required
							type="text"
							class="w-full rounded-xl text-[#111818] dark:text-white border border-[#d5e2e2] dark:border-gray-700 bg-white dark:bg-background-dark focus:border-[#2c7677] focus:ring-1 focus:ring-[#2c7677] h-12 pl-10 pr-4 text-sm font-normal placeholder:text-[#8B949E] transition-colors"
							placeholder="John Doe"
						/>
					</div>
				</div>

				<!-- Email Address Field -->
				<div class="flex flex-col gap-2">
					<label
						for="email"
						class="text-[#111818] dark:text-gray-200 text-sm font-semibold"
					>
						Email Address
					</label>
					<div class="relative flex items-center">
						<span
							class="absolute left-3 text-[#5e8787] material-symbols-outlined"
							style="font-size: 20px"
						>
							mail
						</span>
						<input
							id="email"
							v-model="email"
							required
							type="email"
							class="w-full rounded-xl text-[#111818] dark:text-white border border-[#d5e2e2] dark:border-gray-700 bg-white dark:bg-background-dark focus:border-[#2c7677] focus:ring-1 focus:ring-[#2c7677] h-12 pl-10 pr-4 text-sm font-normal placeholder:text-[#8B949E] transition-colors"
							placeholder="name@company.com"
						/>
					</div>
				</div>

				<!-- Phone Number Field -->
				<div class="flex flex-col gap-2">
					<label
						for="phone"
						class="text-[#111818] dark:text-gray-200 text-sm font-semibold"
					>
						Phone Number
					</label>
					<div class="relative flex items-center">
						<span
							class="absolute left-3 text-[#5e8787] material-symbols-outlined"
							style="font-size: 20px"
						>
							phone
						</span>
						<input
							id="phone"
							v-model="phone"
							required
							type="tel"
							class="w-full rounded-xl text-[#111818] dark:text-white border border-[#d5e2e2] dark:border-gray-700 bg-white dark:bg-background-dark focus:border-[#2c7677] focus:ring-1 focus:ring-[#2c7677] h-12 pl-10 pr-4 text-sm font-normal placeholder:text-[#8B949E] transition-colors"
							placeholder="+1 (555) 000-0000"
						/>
					</div>
				</div>

				<!-- Password Field -->
				<div class="flex flex-col gap-2">
					<label
						for="password"
						class="text-[#111818] dark:text-gray-200 text-sm font-semibold"
					>
						Password
					</label>
					<div class="relative flex items-center">
						<span
							class="absolute left-3 text-[#5e8787] material-symbols-outlined"
							style="font-size: 20px"
						>
							lock
						</span>
						<input
							id="password"
							v-model="password"
							required
							:type="showPassword ? 'text' : 'password'"
							class="w-full rounded-xl text-[#111818] dark:text-white border border-[#d5e2e2] dark:border-gray-700 bg-white dark:bg-background-dark focus:border-[#2c7677] focus:ring-1 focus:ring-[#2c7677] h-12 pl-10 pr-12 text-sm font-normal placeholder:text-[#8B949E] transition-colors"
							placeholder="••••••••"
							minlength="8"
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
					<p class="text-xs text-[#5e8787]">Must be at least 8 characters long.</p>
				</div>

				<!-- Terms and Conditions -->
				<div class="flex items-start gap-2">
					<input
						id="terms"
						v-model="agreeToTerms"
						type="checkbox"
						required
						class="size-4 mt-0.5 rounded border-[#d5e2e2] text-[#2c7677] focus:ring-[#2c7677]"
					/>
					<label for="terms" class="text-xs text-[#5e8787] font-medium select-none">
						I agree to the
						<a href="#" class="text-[#2c7677] hover:underline">Terms of Service</a>
						and
						<a href="#" class="text-[#2c7677] hover:underline">Privacy Policy</a>
					</label>
				</div>

				<!-- Error Message -->
				<div v-if="errorMessage" class="p-3 rounded-lg bg-red-50 border border-red-200">
					<p class="text-sm text-red-600">{{ errorMessage }}</p>
				</div>

				<!-- Create Account Button -->
				<button
					type="submit"
					:disabled="loading"
					class="w-full flex items-center justify-center rounded-xl h-12 bg-[#2c7677] text-white text-sm font-bold shadow-lg shadow-[#2c7677]/20 hover:brightness-110 active:scale-[0.98] transition-all disabled:opacity-70 disabled:cursor-not-allowed"
				>
					<svg
						v-if="loading"
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
					<span v-if="!loading">Create Account</span>
					<span v-else>Creating account...</span>
				</button>
			</form>

			<!-- Login Link -->
			<div class="mt-6 text-center">
				<p class="text-sm text-[#5e8787]">
					Already have an account?
					<RouterLink to="/login" class="text-[#2c7677] font-bold hover:underline">
						Log in
					</RouterLink>
				</p>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { createResource } from "frappe-ui";

const router = useRouter();

// Form fields
const fullName = ref("");
const email = ref("");
const phone = ref("");
const password = ref("");
const agreeToTerms = ref(false);
const showPassword = ref(false);
const loading = ref(false);
const errorMessage = ref("");

async function submit() {
	if (!agreeToTerms.value) {
		errorMessage.value = "You must agree to the Terms of Service and Privacy Policy";
		return;
	}

	loading.value = true;
	errorMessage.value = "";

	try {
		// Split full name into first and last name
		const nameParts = fullName.value.trim().split(" ");
		const firstName = nameParts[0];
		const lastName = nameParts.slice(1).join(" ") || firstName;

		const createUserResource = createResource({
			url: "frappoint.frappoint.api.user.create_user",
			makeParams() {
				return {
					email: email.value,
					first_name: firstName,
					last_name: lastName,
					phone: phone.value,
					password: password.value,
				};
			},
		});

		await createUserResource.submit();

		// Redirect to login page with success message
		router.push({
			name: "Login",
			query: { registered: "true" },
		});
	} catch (error) {
		errorMessage.value =
			error.messages?.[0] || error.message || "Failed to create account. Please try again.";
	} finally {
		loading.value = false;
	}
}
</script>
