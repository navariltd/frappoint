<template>
	<Teleport to="body">
		<div
			v-if="visible"
			class="fixed inset-0 z-50 flex items-center justify-center bg-on-surface/50 backdrop-blur-sm"
		>
			<div
				class="bg-surface rounded-2xl p-8 max-w-sm w-full mx-4 shadow-2xl text-center space-y-5"
			>
				<!-- Icon / Spinner -->
				<div
					v-if="progress === 'processing' || progress === 'redirecting'"
					class="flex justify-center"
				>
					<div
						class="w-14 h-14 border-4 border-primary/20 border-t-primary rounded-full animate-spin"
					></div>
				</div>
				<div v-else class="flex justify-center">
					<div
						class="w-14 h-14 rounded-full bg-tertiary-container flex items-center justify-center"
					>
						<span class="material-symbols-outlined text-tertiary text-[32px]"
							>smartphone</span
						>
					</div>
				</div>

				<!-- Message -->
				<div class="space-y-2">
					<h3 class="text-headline-sm font-headline-sm text-on-surface">
						{{ title }}
					</h3>
					<p class="text-body-sm text-on-surface-variant">{{ message }}</p>
				</div>

				<!-- Cancel option for MPesa -->
				<button
					v-if="onCancel"
					class="text-label-md text-on-surface-variant underline"
					type="button"
					@click="onCancel"
				>
					Cancel
				</button>
			</div>
		</div>
	</Teleport>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { PaymentProgress } from "@/stores/checkout.store";

const props = defineProps<{
	progress: PaymentProgress;
	message?: string;
	onCancel?: () => void;
}>();

const visible = computed(
	() => props.progress === "processing" || props.progress === "redirecting"
);

const title = computed(() => {
	if (props.progress === "redirecting") return "Redirecting";
	return "Processing Payment";
});
</script>
