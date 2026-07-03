<template>
	<div class="space-y-3">
		<CouponInput
			:model-value="couponDraft"
			:loading="loading"
			:disabled="submitting"
			@update:model-value="$emit('update:draft', $event)"
			@apply="$emit('apply')"
		/>

		<CouponValidationMessage :message="errorMessage" type="error" />
		<CouponValidationMessage :message="successMessage" type="success" />

		<AppliedCouponCard
			v-if="appliedCoupon"
			:coupon-code="appliedCoupon.coupon"
			:discount-amount="appliedCoupon.discountAmount"
			:appointments="appliedCoupon.appointments"
			:currency="currency"
		>
			<CouponRemovalAction :loading="loading" @remove="$emit('remove')" />
		</AppliedCouponCard>
	</div>
</template>

<script setup lang="ts">
import CouponInput from "./CouponInput.vue";
import CouponValidationMessage from "./CouponValidationMessage.vue";
import AppliedCouponCard from "./AppliedCouponCard.vue";
import CouponRemovalAction from "./CouponRemovalAction.vue";
import type { AppliedCoupon } from "@/services/checkout.service";

defineProps<{
	couponDraft: string;
	currency: string;
	appliedCoupon: AppliedCoupon | null;
	errorMessage: string;
	successMessage: string;
	loading: boolean;
	submitting: boolean;
}>();

defineEmits<{
	"update:draft": [value: string];
	apply: [];
	remove: [];
}>();
</script>
