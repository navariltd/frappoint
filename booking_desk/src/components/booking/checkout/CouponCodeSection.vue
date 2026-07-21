<template>
	<section class="rounded-xl border border-outline-variant bg-surface p-4 space-y-3">
		<div class="flex items-start justify-between gap-3">
			<div>
				<h3 class="text-[14px] font-semibold text-on-surface">Coupon Code</h3>
				<p class="text-[12px] text-on-surface-variant">
					Apply a booking-level discount before taking payment.
				</p>
			</div>
			<span
				v-if="appliedCoupon"
				class="rounded-full bg-secondary-container px-2 py-1 text-[10px] font-semibold text-on-secondary-container"
			>
				Applied
			</span>
		</div>

		<div class="flex flex-col sm:flex-row gap-2">
			<input
				:value="couponDraft"
				type="text"
				class="min-w-0 flex-1 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] font-semibold uppercase text-on-surface outline-none focus:border-primary"
				placeholder="Enter coupon code"
				:disabled="isSubmitting || loading"
				@input="$emit('update:couponDraft', $event.target.value)"
				@keydown.enter.prevent="$emit('apply')"
			/>
			<button
				type="button"
				class="rounded-lg px-4 py-2 text-[12px] font-semibold transition-colors"
				:class="
					canApply
						? 'bg-primary text-on-primary hover:bg-primary/90'
						: 'bg-primary/60 text-on-primary cursor-not-allowed'
				"
				:disabled="!canApply"
				@click="$emit('apply')"
			>
				{{ loading ? "Checking..." : "Apply" }}
			</button>
		</div>

		<p v-if="couponError" class="text-[12px] text-error">{{ couponError }}</p>
		<p v-else-if="couponMessage" class="text-[12px] text-secondary">{{ couponMessage }}</p>

		<div
			v-if="validation?.valid"
			class="rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-[12px] text-on-surface"
		>
			<div class="flex items-center justify-between gap-3">
				<span class="font-semibold">{{ validationMessage }}</span>
				<span class="text-primary font-semibold">
					-{{ currency }} {{ previewDiscount.toFixed(2) }}
				</span>
			</div>
		</div>

		<div
			v-if="appliedCoupon"
			class="rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 space-y-2"
		>
			<div class="flex items-start justify-between gap-3">
				<div>
					<p class="text-[12px] font-semibold text-on-surface">
						{{ appliedCouponCode }}
					</p>
					<p class="text-[11px] text-on-surface-variant">
						Discount {{ currency }} {{ appliedDiscount.toFixed(2) }}
					</p>
				</div>
				<button
					type="button"
					class="rounded-lg border border-outline-variant px-3 py-1.5 text-[11px] font-semibold text-on-surface-variant hover:bg-surface-container transition-colors"
					:disabled="isSubmitting || loading"
					@click="$emit('remove')"
				>
					Remove
				</button>
			</div>
		</div>
	</section>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	couponDraft: { type: String, default: "" },
	currency: { type: String, default: "KES" },
	appliedCoupon: { type: Object, default: null },
	validation: { type: Object, default: null },
	couponError: { type: String, default: "" },
	couponMessage: { type: String, default: "" },
	isValidating: { type: Boolean, default: false },
	isApplying: { type: Boolean, default: false },
	isSubmitting: { type: Boolean, default: false },
});

defineEmits(["update:couponDraft", "apply", "remove"]);

const loading = computed(() => props.isValidating || props.isApplying);
const canApply = computed(
	() => Boolean(props.couponDraft?.trim()) && !props.isSubmitting && !loading.value
);
const previewDiscount = computed(() => Number(props.validation?.evaluation?.previewDiscount || 0));
const validationMessage = computed(() => props.validation?.message || "Coupon is valid.");
const appliedCouponCode = computed(
	() =>
		props.appliedCoupon?.code || props.appliedCoupon?.coupon || props.appliedCoupon?.name || ""
);
const appliedDiscount = computed(() =>
	Number(props.appliedCoupon?.discountAmount || props.appliedCoupon?.discount_amount || 0)
);
</script>
