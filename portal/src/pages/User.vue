<template>
	<div class="min-h-screen bg-[#fafafa] dark:bg-[#16191d] pb-32">
		<Alert
			v-if="alertOptions.message"
			:title="alertOptions.title"
			:description="alertOptions.message"
			:variant="alertOptions.variant"
			:theme="alertOptions.theme"
			class="fixed top-8 left-1/2 -translate-x-1/2 z-50 min-w-[300px]"
			@close="alertOptions.message = ''"
		/>
		<div class="max-w-[1000px] mx-auto px-4 md:px-8 py-6 md:py-10">
			<!-- Header Section -->
			<header
				class="flex flex-col md:flex-row md:justify-between md:items-center gap-6 mb-10"
			>
				<div class="flex items-center gap-4 md:gap-6">
					<div class="relative group">
						<div
							class="w-20 h-20 md:w-28 md:h-28 rounded-full border-4 border-white dark:border-gray-700 shadow-md overflow-hidden bg-gray-200"
						>
							<img
								v-if="auth.userImage"
								:src="auth.userImage"
								:alt="`Profile picture of ${auth.userName}`"
								class="w-full h-full object-cover"
							/>
							<div
								v-else
								class="w-full h-full flex items-center justify-center bg-primary/10"
							>
								<span
									class="material-symbols-outlined text-primary text-5xl md:text-7xl"
								>
									person
								</span>
							</div>
						</div>
						<!-- Upload button overlay -->
						<FileUploader
							:fileTypes="['image/*']"
							:uploadArgs="{
								doctype: 'User',
								docname: auth.userId,
								fieldname: 'user_image',
								private: false,
								optimize: true,
								max_width: 400,
								max_height: 400,
							}"
							@success="handleImageUpload"
						>
							<template #default="{ openFileSelector, uploading, progress }">
								<button
									@click="openFileSelector"
									:disabled="uploading"
									class="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-full cursor-pointer disabled:cursor-wait"
								>
									<div class="flex flex-col items-center gap-1">
										<span
											v-if="!uploading"
											class="material-symbols-outlined text-white text-2xl md:text-3xl"
										>
											camera_alt
										</span>
										<span v-else class="text-white text-xs font-medium">
											{{ progress }}%
										</span>
										<span
											class="text-white text-[10px] md:text-xs font-medium"
										>
											{{ uploading ? "Uploading..." : "Change" }}
										</span>
									</div>
								</button>
							</template>
						</FileUploader>
					</div>
					<div class="flex flex-col">
						<h2
							class="text-2xl md:text-3xl font-extrabold text-[#0f1a19] dark:text-white tracking-tight"
						>
							{{ userDetails?.full_name || auth.userName }}
						</h2>
						<p class="text-[#55918c] font-medium flex items-center gap-1.5 mt-1">
							<span class="material-symbols-outlined text-sm">verified</span>
							Member
						</p>
					</div>
				</div>
			</header>

			<!-- Personal Information Section -->
			<div class="grid grid-cols-1 gap-8">
				<section
					class="bg-white dark:bg-[#1e2329] border border-[#d2e5e3] dark:border-[#2d3736] rounded-xl shadow-sm overflow-hidden"
				>
					<div
						class="px-4 md:px-6 py-5 border-b border-[#d2e5e3] dark:border-[#2d3736] flex items-center gap-2"
					>
						<span class="material-symbols-outlined text-primary">badge</span>
						<h3 class="text-lg font-bold">Personal Information</h3>
					</div>
					<div class="p-4 md:p-6">
						<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
							<div class="flex flex-col gap-2">
								<label
									class="text-sm font-bold text-gray-700 dark:text-gray-300"
									for="firstName"
								>
									First Name
								</label>
								<input
									id="firstName"
									v-model="formData.firstName"
									class="form-input w-full rounded-xl border-[#d2e5e3] dark:border-[#2d3736] bg-[#fafafa] dark:bg-[#16191d] focus:border-primary focus:ring-1 focus:ring-primary transition-all p-3.5 text-base"
									type="text"
									placeholder="First name"
								/>
							</div>
							<div class="flex flex-col gap-2">
								<label
									class="text-sm font-bold text-gray-700 dark:text-gray-300"
									for="lastName"
								>
									Last Name
								</label>
								<input
									id="lastName"
									v-model="formData.lastName"
									class="form-input w-full rounded-xl border-[#d2e5e3] dark:border-[#2d3736] bg-[#fafafa] dark:bg-[#16191d] focus:border-primary focus:ring-1 focus:ring-primary transition-all p-3.5 text-base"
									type="text"
									placeholder="Last name"
								/>
							</div>
							<div class="flex flex-col gap-2 md:col-span-2">
								<label
									class="text-sm font-bold text-gray-700 dark:text-gray-300"
									for="email"
								>
									Email Address
								</label>
								<div class="relative">
									<input
										id="email"
										v-model="formData.email"
										class="form-input w-full rounded-xl border-[#d2e5e3] dark:border-[#2d3736] bg-[#fafafa] dark:bg-[#16191d] focus:border-primary focus:ring-1 focus:ring-primary transition-all p-3.5 pl-11 text-base hover:cursor-not-allowed"
										type="email"
										placeholder="email@example.com"
										disabled
									/>
									<span
										class="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400"
									>
										mail
									</span>
								</div>
							</div>
							<div class="flex flex-col gap-2 md:col-span-2">
								<label
									class="text-sm font-bold text-gray-700 dark:text-gray-300"
									for="phone"
								>
									Phone Number
								</label>
								<div class="relative">
									<input
										id="phone"
										v-model="formData.phone"
										class="form-input w-full rounded-xl border-[#d2e5e3] dark:border-[#2d3736] bg-[#fafafa] dark:bg-[#16191d] focus:border-primary focus:ring-1 focus:ring-primary transition-all p-3.5 pl-11 text-base"
										type="tel"
										placeholder="+1 (555) 000-0000"
									/>
									<span
										class="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400"
									>
										call
									</span>
								</div>
							</div>
						</div>
					</div>
				</section>

				<!-- Security Section -->
				<section
					class="bg-white dark:bg-[#1e2329] border border-[#d2e5e3] dark:border-[#2d3736] rounded-xl shadow-sm overflow-hidden"
				>
					<div
						class="px-4 md:px-6 py-5 border-b border-[#d2e5e3] dark:border-[#2d3736] flex items-center gap-2"
					>
						<span class="material-symbols-outlined text-primary">security</span>
						<h3 class="text-lg font-bold">Security</h3>
					</div>
					<div class="p-4 md:p-6">
						<div class="flex flex-col gap-6">
							<div class="flex flex-col gap-2">
								<label
									class="text-sm font-bold text-gray-700 dark:text-gray-300"
									for="currentPassword"
								>
									Current Password
								</label>
								<div class="relative">
									<input
										id="currentPassword"
										v-model="passwordData.currentPassword"
										:type="showCurrentPassword ? 'text' : 'password'"
										class="form-input w-full rounded-xl border-[#d2e5e3] dark:border-[#2d3736] bg-[#fafafa] dark:bg-[#16191d] focus:border-primary focus:ring-1 focus:ring-primary transition-all p-3.5 pr-12 text-base"
										placeholder="••••••••••••"
									/>
									<button
										type="button"
										class="absolute right-3 top-1/2 -translate-y-1/2 text-[#5e8787] flex items-center hover:text-primary transition-colors select-none outline-none focus:outline-none"
										@click="showCurrentPassword = !showCurrentPassword"
									>
										<span
											class="material-symbols-outlined"
											style="font-size: 20px"
										>
											{{
												showCurrentPassword
													? "visibility_off"
													: "visibility"
											}}
										</span>
									</button>
								</div>
							</div>
							<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
								<div class="flex flex-col gap-2">
									<label
										class="text-sm font-bold text-gray-700 dark:text-gray-300"
										for="newPassword"
									>
										New Password
									</label>
									<div class="relative">
										<input
											id="newPassword"
											v-model="passwordData.newPassword"
											:type="showNewPassword ? 'text' : 'password'"
											class="form-input w-full rounded-xl border-[#d2e5e3] dark:border-[#2d3736] bg-[#fafafa] dark:bg-[#16191d] focus:border-primary focus:ring-1 focus:ring-primary transition-all p-3.5 pr-12 text-base"
											placeholder="Create a new password"
										/>
										<button
											type="button"
											class="absolute right-3 top-1/2 -translate-y-1/2 text-[#5e8787] flex items-center hover:text-primary transition-colors select-none outline-none focus:outline-none"
											@click="showNewPassword = !showNewPassword"
										>
											<span
												class="material-symbols-outlined"
												style="font-size: 20px"
											>
												{{
													showNewPassword
														? "visibility_off"
														: "visibility"
												}}
											</span>
										</button>
									</div>
								</div>
								<div class="flex flex-col gap-2">
									<label
										class="text-sm font-bold text-gray-700 dark:text-gray-300"
										for="confirmPassword"
									>
										Confirm New Password
									</label>
									<div class="relative">
										<input
											id="confirmPassword"
											v-model="passwordData.confirmPassword"
											:type="showConfirmPassword ? 'text' : 'password'"
											class="form-input w-full rounded-xl border-[#d2e5e3] dark:border-[#2d3736] bg-[#fafafa] dark:bg-[#16191d] focus:border-primary focus:ring-1 focus:ring-primary transition-all p-3.5 pr-12 text-base"
											placeholder="Repeat new password"
										/>
										<button
											type="button"
											class="absolute right-3 top-1/2 -translate-y-1/2 text-[#5e8787] flex items-center hover:text-primary transition-colors select-none outline-none focus:outline-none"
											@click="showConfirmPassword = !showConfirmPassword"
										>
											<span
												class="material-symbols-outlined"
												style="font-size: 20px"
											>
												{{
													showConfirmPassword
														? "visibility_off"
														: "visibility"
												}}
											</span>
										</button>
									</div>
								</div>
							</div>
							<div
								class="flex items-center gap-2 bg-primary/10 p-3 rounded-lg border border-primary/20"
							>
								<span class="material-symbols-outlined text-primary text-[20px]">
									info
								</span>
								<p class="text-xs text-primary font-semibold">
									Password must be at least 8 characters long and include a mix
									of numbers and symbols.
								</p>
							</div>
						</div>
					</div>
				</section>
			</div>
		</div>

		<!-- Fixed Footer with Action Buttons -->
		<footer
			class="fixed bottom-0 left-0 right-0 bg-white/90 dark:bg-[#16191d]/90 backdrop-blur-md border-t border-[#d2e5e3] dark:border-[#2d3736] px-4 md:px-10 py-4 md:py-5 z-20 flex flex-col md:flex-row justify-end gap-3 md:gap-4 items-stretch md:items-center"
		>
			<button
				@click="discardChanges"
				class="text-sm font-bold text-gray-500 hover:text-[#0f1a19] dark:hover:text-white transition-colors py-2 md:py-0 md:mr-4"
			>
				Discard Changes
			</button>
			<button
				@click="saveChanges"
				:disabled="saving || !hasChanges"
				class="bg-primary hover:bg-primary/90 text-white font-bold py-3 px-6 md:px-8 rounded-xl shadow-md flex items-center justify-center gap-2 transform active:scale-95 transition-all disabled:opacity-70 disabled:cursor-not-allowed"
			>
				<svg
					v-if="saving"
					class="animate-spin h-5 w-5 text-white"
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
				<span class="material-symbols-outlined text-[18px]" v-else>save</span>
				<span v-if="!saving">Save Changes</span>
				<span v-else>Saving...</span>
			</button>
		</footer>
	</div>
</template>

<script setup>
import { useAuthStore } from "@/stores/auth";
import { ref, onMounted, computed } from "vue";
import { useAlert } from "@/composables/useAlert";
import { createResource, FileUploader, Alert } from "frappe-ui";

const auth = useAuthStore();
const userDetails = ref(null);
const saving = ref(false);
const showCurrentPassword = ref(false);
const showNewPassword = ref(false);
const showConfirmPassword = ref(false);

const { alertOptions, showAlert } = useAlert();

const formData = ref({
	firstName: "",
	lastName: "",
	email: "",
	phone: "",
});

const passwordData = ref({
	currentPassword: "",
	newPassword: "",
	confirmPassword: "",
});

// Computed property to check if there are any changes
const hasChanges = computed(() => {
	if (!userDetails.value) return false;

	const nameParts = userDetails.value.full_name?.split(" ") || [];
	const originalFirstName = nameParts[0] || "";
	const originalLastName = nameParts.slice(1).join(" ") || "";
	const originalPhone = userDetails.value.phone || "";

	const profileChanged =
		formData.value.firstName !== originalFirstName ||
		formData.value.lastName !== originalLastName ||
		formData.value.phone !== originalPhone;

	const passwordChanged =
		!!passwordData.value.currentPassword ||
		!!passwordData.value.newPassword ||
		!!passwordData.value.confirmPassword;

	return profileChanged || passwordChanged;
});

// Fetch user details
const getUserDetails = createResource({
	url: "frappoint.frappoint.api.user.get_user_details",
	auto: true,
	onSuccess(data) {
		userDetails.value = data;
		const nameParts = data.full_name?.split(" ") || [];
		formData.value = {
			firstName: nameParts[0] || "",
			lastName: nameParts.slice(1).join(" ") || "",
			email: data.email || "",
			phone: data.phone || "",
		};
	},
});

function discardChanges() {
	// Reset form to original values
	if (userDetails.value) {
		const nameParts = userDetails.value.full_name?.split(" ") || [];
		formData.value = {
			firstName: nameParts[0] || "",
			lastName: nameParts.slice(1).join(" ") || "",
			email: userDetails.value.email || "",
			phone: userDetails.value.phone || "",
		};
	}
	passwordData.value = {
		currentPassword: "",
		newPassword: "",
		confirmPassword: "",
	};
}

async function saveChanges() {
	saving.value = true;
	let profileUpdated = false;
	let passwordUpdated = false;

	try {
		// Check if profile information has changed
		const nameParts = userDetails.value?.full_name?.split(" ") || [];
		const originalFirstName = nameParts[0] || "";
		const originalLastName = nameParts.slice(1).join(" ") || "";
		const originalPhone = userDetails.value?.phone || "";

		const profileChanged =
			formData.value.firstName !== originalFirstName ||
			formData.value.lastName !== originalLastName ||
			formData.value.phone !== originalPhone;

		// Update profile if changed
		if (profileChanged) {
			const updateProfileResource = createResource({
				url: "frappoint.frappoint.api.user.update_user_profile",
				makeParams() {
					return {
						first_name: formData.value.firstName,
						last_name: formData.value.lastName,
						phone: formData.value.phone,
					};
				},
			});

			await updateProfileResource.submit();
			profileUpdated = true;
			// Refresh user details
			await getUserDetails.fetch();
		}

		// Check if password fields are filled
		const passwordFilled =
			passwordData.value.currentPassword ||
			passwordData.value.newPassword ||
			passwordData.value.confirmPassword;

		// Update password if any password field is filled
		if (passwordFilled) {
			// Validate all password fields are filled
			if (
				!passwordData.value.currentPassword ||
				!passwordData.value.newPassword ||
				!passwordData.value.confirmPassword
			) {
				throw new Error("All password fields are required to change password");
			}

			// Validate passwords match
			if (passwordData.value.newPassword !== passwordData.value.confirmPassword) {
				throw new Error("New password and confirm password do not match");
			}

			const updatePasswordResource = createResource({
				url: "frappoint.frappoint.api.user.update_user_password",
				makeParams() {
					return {
						current_password: passwordData.value.currentPassword,
						new_password: passwordData.value.newPassword,
						confirm_password: passwordData.value.confirmPassword,
					};
				},
			});

			await updatePasswordResource.submit();
			passwordUpdated = true;
			// Clear password fields after successful update
			passwordData.value = {
				currentPassword: "",
				newPassword: "",
				confirmPassword: "",
			};
		}

		// Show success message and reload page
		if (profileUpdated && passwordUpdated) {
			showAlert("Success", "Profile and password updated successfully!");
		} else if (profileUpdated) {
			showAlert("Success", "Profile updated successfully!");
		} else if (passwordUpdated) {
			showAlert("Success", "Password updated successfully!");
		} else {
			showAlert("Info", "No changes detected", "gray");
		}
	} catch (error) {
		console.error("Error saving changes:", error);
		const errorMessage =
			error.messages?.[0] || error.message || "Failed to save changes. Please try again.";
		showAlert("Error", errorMessage, "red");
	} finally {
		saving.value = false;
	}
}

function handleImageUpload(file) {
	const updateImageResource = createResource({
		url: "frappoint.frappoint.api.user.update_user_image",
		makeParams() {
			return {
				file_url: file.file_url,
			};
		},
	});

	updateImageResource
		.submit()
		.then(() => {
			window.location.reload();
		})
		.catch((error) => {
			console.error("Error updating profile image:", error);
			showAlert("Error", "Failed to update profile image. Please try again.", "red");
		});
}

onMounted(() => {
	getUserDetails.fetch();
});
</script>
