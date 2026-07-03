<template>
	<div class="min-h-screen w-full flex items-center justify-center bg-surface-container-low p-4">
		<div
			class="max-w-md w-full rounded-2xl border border-outline-variant bg-surface-container-lowest shadow-sm p-8 text-center space-y-6"
		>
			<!-- Error Icon -->
			<div class="flex justify-center">
				<div
					class="w-16 h-16 rounded-full bg-error-container/30 flex items-center justify-center"
				>
					<svg
						class="w-8 h-8 text-error"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 8v4m0 4v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
				</div>
			</div>

			<!-- Error Code -->
			<div>
				<h1 class="text-4xl font-bold text-on-surface">403</h1>
				<p class="text-sm text-on-surface-variant mt-1">Access Forbidden</p>
			</div>

			<!-- Error Message -->
			<div class="space-y-2">
				<p class="text-on-surface font-medium">Permission Denied</p>
				<p class="text-sm text-on-surface-variant">
					You don't have the required permissions to access this application. Please
					contact your administrator for access.
				</p>
			</div>

			<!-- Action Button -->
			<button
				type="button"
				class="w-full px-4 py-3 rounded-lg bg-primary text-on-primary font-medium text-sm transition-colors hover:bg-primary/90"
				@click="handleLogout"
			>
				Log Out
			</button>

			<!-- Support Link -->
			<div class="text-center">
				<p class="text-xs text-on-surface-variant">
					Need help?
					<a
						href="mailto:support@example.com"
						class="text-primary font-medium hover:underline"
					>
						Contact Support
					</a>
				</p>
			</div>
		</div>
	</div>
</template>

<script setup>
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

const handleLogout = async () => {
	await auth.logout();
};
</script>
