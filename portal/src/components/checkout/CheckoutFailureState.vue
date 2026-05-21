<template>
	<div class="flex-1 flex items-center justify-center p-8">
		<div class="max-w-md w-full text-center space-y-6">
			<div
				class="w-20 h-20 rounded-full bg-error-container flex items-center justify-center mx-auto"
			>
				<span class="material-symbols-outlined text-error text-[40px]">error_outline</span>
			</div>
			<div class="space-y-2">
				<h2 class="text-headline-md font-headline-md text-on-surface">Payment Failed</h2>
				<p class="text-body-md text-on-surface-variant">
					{{ message || "Something went wrong. Please try again." }}
				</p>
			</div>
			<div class="flex flex-col gap-3">
				<button
					v-if="onRetry"
					class="w-full py-3 rounded-xl bg-primary text-on-primary font-semibold hover:opacity-90"
					type="button"
					@click="onRetry"
				>
					Try Again
				</button>
				<button
					v-if="onCancel"
					class="text-body-sm text-on-surface-variant hover:text-on-surface transition-colors"
					type="button"
					@click="onCancel"
				>
					Cancel
				</button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
defineProps<{
	message?: string;
	onRetry?: () => void;
	onCancel?: () => void;
}>();
</script>
