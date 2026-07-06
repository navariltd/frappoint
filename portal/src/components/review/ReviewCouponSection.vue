<template>
	<div
		class="glass-card rounded-xl p-6 space-y-4"
		:class="{ 'opacity-60 pointer-events-none': isDisabled }"
	>
		<h3 class="text-headline-sm font-headline-sm text-on-surface flex items-center gap-2">
			<span class="material-symbols-outlined text-primary text-[20px]">local_offer</span>
			Apply Coupon
		</h3>

		<!-- Disabled state notice -->
		<div
			v-if="isDisabled"
			class="flex items-center gap-2 rounded-lg bg-surface-container-high border border-outline-variant/30 px-4 py-3"
		>
			<span class="material-symbols-outlined text-on-surface-variant text-[18px]">info</span>
			<p class="text-body-sm text-on-surface-variant">
				Appointment-level discounts active — remove them to use a booking coupon.
			</p>
		</div>

		<!-- Applied coupon badge -->
		<div
			v-else-if="hasApplied"
			class="flex items-center justify-between gap-3 rounded-lg bg-secondary-container/30 border border-secondary/20 px-4 py-3"
		>
			<div class="flex items-center gap-2">
				<span class="material-symbols-outlined text-secondary text-[18px]"
					>check_circle</span
				>
				<div>
					<p class="text-body-sm font-semibold text-on-surface">{{ appliedCode }}</p>
					<p class="text-label-sm text-on-surface-variant">
						Coupon applied
						<template v-if="(discountAmount ?? 0) > 0">
							– saving {{ fmt(discountAmount ?? 0) }}
						</template>
					</p>
				</div>
			</div>
			<button
				:disabled="isRemoving"
				class="flex items-center gap-1 text-label-sm font-semibold text-error hover:opacity-75 transition-opacity disabled:opacity-40"
				@click="$emit('remove')"
			>
				<span
					v-if="isRemoving"
					class="w-3.5 h-3.5 border-2 border-error/30 border-t-error rounded-full animate-spin"
				></span>
				<span v-else class="material-symbols-outlined text-[16px]">close</span>
				Remove
			</button>
		</div>

		<!-- Coupon input row -->
		<div v-else class="space-y-2">
			<div class="flex gap-2">
				<input
					:value="modelValue"
					type="text"
					placeholder="Enter coupon code"
					:disabled="isApplying"
					class="flex-1 px-4 py-2.5 rounded-lg border border-outline-variant/40 bg-surface-container text-body-md text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all disabled:opacity-50"
					@input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
					@keydown.enter.prevent="$emit('apply')"
				/>
				<button
					:disabled="isApplying || !modelValue?.trim()"
					class="px-5 py-2.5 rounded-lg bg-primary text-on-primary font-semibold text-body-sm hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 shrink-0"
					@click="$emit('apply')"
				>
					<span
						v-if="isApplying"
						class="w-4 h-4 border-2 border-on-primary/30 border-t-on-primary rounded-full animate-spin"
					></span>
					<span v-else>Apply</span>
				</button>
			</div>

			<!-- Error message -->
			<p v-if="errorMessage" class="text-label-sm text-error flex items-center gap-1.5">
				<span class="material-symbols-outlined text-[14px]">error</span>
				{{ errorMessage }}
			</p>
		</div>

		<!-- Success message -->
		<p
			v-if="successMessage && !hasApplied && !isDisabled"
			class="text-label-sm text-secondary flex items-center gap-1.5"
		>
			<span class="material-symbols-outlined text-[14px]">check_circle</span>
			{{ successMessage }}
		</p>
	</div>
</template>

<script setup lang="ts">
import { formatCurrency } from "@/utils";

const props = defineProps<{
	modelValue: string;
	appliedCode?: string;
	discountAmount?: number;
	currency: string;
	hasApplied: boolean;
	isApplying: boolean;
	isRemoving: boolean;
	errorMessage: string;
	successMessage: string;
	isDisabled?: boolean;
}>();

defineEmits<{
	"update:modelValue": [value: string];
	apply: [];
	remove: [];
}>();

function fmt(amount: number) {
	return formatCurrency(Number(amount || 0), props.currency);
}
</script>
