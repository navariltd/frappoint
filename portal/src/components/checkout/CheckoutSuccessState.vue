<template>
	<div class="flex-1 flex items-center justify-center p-8">
		<div class="max-w-md w-full text-center space-y-6">
			<div
				class="w-20 h-20 rounded-full bg-secondary-container flex items-center justify-center mx-auto"
			>
				<span
					class="material-symbols-outlined text-secondary text-[40px]"
					style="font-variation-settings: 'FILL' 1"
				>
					check_circle
				</span>
			</div>
			<div class="space-y-2">
				<h2 class="text-headline-md font-headline-md text-on-surface">
					Booking Confirmed!
				</h2>
				<p class="text-body-md text-on-surface-variant">
					{{ message || "Your payment was received successfully." }}
				</p>
			</div>
			<div v-if="bookingId" class="bg-surface-container rounded-xl p-4">
				<p class="text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">
					Booking Reference
				</p>
				<p class="text-body-lg font-bold text-on-surface">{{ bookingId }}</p>
			</div>
			<div class="flex flex-col gap-3">
				<button
					v-if="onViewBooking"
					class="w-full py-3 rounded-xl bg-primary text-on-primary font-semibold hover:opacity-90"
					type="button"
					@click="onViewBooking"
				>
					View Booking
				</button>
				<button
					v-if="onHome"
					class="text-body-sm text-on-surface-variant hover:text-primary transition-colors"
					type="button"
					@click="onHome"
				>
					Back to Home
				</button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
defineProps<{
	message?: string;
	bookingId?: string;
	onViewBooking?: () => void;
	onHome?: () => void;
}>();
</script>
