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

		<label class="block space-y-1">
			<span class="text-[12px] font-semibold text-on-surface">Complimentary coupon</span>
			<select
				:value="selectedComplimentaryCode"
				class="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface outline-none focus:border-primary"
				:disabled="
					isSubmitting || loading || couponsLoading || !complimentaryCoupons.length
				"
				@change="selectCoupon($event.target.value)"
			>
				<option value="">
					{{ couponsLoading ? "Loading coupons..." : "Select a complimentary coupon" }}
				</option>
				<option
					v-for="coupon in complimentaryCoupons"
					:key="coupon.name"
					:value="coupon.code || coupon.name"
				>
					{{ coupon.code || coupon.name }}
				</option>
			</select>
		</label>
		<p v-if="couponsLoadError" role="alert" class="text-[12px] text-error">
			{{ couponsLoadError }}
			<button
				type="button"
				class="underline"
				:disabled="couponsLoading || isSubmitting || loading"
				@click="loadComplimentaryCoupons"
			>
				Retry
			</button>
		</p>
		<p
			v-else-if="!couponsLoading && !complimentaryCoupons.length"
			class="text-[12px] text-on-surface-variant"
		>
			No complimentary coupons available.
		</p>

		<p v-if="loading" role="status" class="text-[12px] text-on-surface-variant">
			{{ isValidating ? "Checking coupon..." : "Updating coupon..." }}
		</p>

		<p v-if="couponError" class="text-[12px] text-error">{{ couponError }}</p>
		<p v-else-if="couponMessage" class="text-[12px] text-secondary-ink">{{ couponMessage }}</p>

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
import { computed, onMounted, ref } from "vue";
import { getComplimentaryCouponsApi } from "@/api/checkout.api";

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

const emit = defineEmits(["update:couponDraft", "apply", "remove"]);

const complimentaryCoupons = ref([]);
const couponsLoading = ref(true);
const couponsLoadError = ref("");
const selectedComplimentaryCode = computed(() =>
	complimentaryCoupons.value.some((coupon) => (coupon.code || coupon.name) === props.couponDraft)
		? props.couponDraft
		: ""
);

async function loadComplimentaryCoupons() {
	couponsLoading.value = true;
	couponsLoadError.value = "";
	try {
		complimentaryCoupons.value = await getComplimentaryCouponsApi();
	} catch {
		couponsLoadError.value = "Could not load complimentary coupons. Please try again.";
	} finally {
		couponsLoading.value = false;
	}
}

onMounted(loadComplimentaryCoupons);

const loading = computed(() => props.isValidating || props.isApplying);
function selectCoupon(code) {
	if (props.isSubmitting || loading.value || couponsLoading.value) return;

	emit("update:couponDraft", code);
	if (code) {
		emit("apply", code);
	} else if (props.appliedCoupon) {
		emit("remove");
	}
}
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
