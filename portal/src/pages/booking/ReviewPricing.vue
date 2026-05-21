<template>
	<div class="min-h-screen bg-surface-bright flex flex-col">
		<!-- Header -->
		<header class="border-b border-outline-variant/20 px-6 py-4 bg-surface">
			<div class="max-w-7xl mx-auto flex items-center gap-2 text-on-surface-variant mb-1">
				<router-link
					:to="{ name: 'Bookings' }"
					class="text-label-sm hover:text-primary transition-colors"
				>
					My Bookings
				</router-link>
				<span class="material-symbols-outlined text-sm">chevron_right</span>
				<span class="text-label-sm uppercase tracking-wider font-semibold text-primary"
					>Review & Pricing</span
				>
			</div>
			<div class="max-w-7xl mx-auto flex items-center justify-between gap-4">
				<div>
					<h1 class="text-headline-lg font-headline-lg text-on-surface">
						Review Your Booking
					</h1>
					<p class="text-body-md text-on-surface-variant">
						Step 3 of 4 — Review appointments, apply a coupon, then proceed to payment.
					</p>
				</div>
				<div class="hidden sm:flex items-center gap-2 text-label-sm">
					<span class="text-on-surface-variant">Cart</span>
					<span class="material-symbols-outlined text-[14px] text-on-surface-variant"
						>arrow_forward</span
					>
					<span class="text-on-surface-variant">Guests</span>
					<span class="material-symbols-outlined text-[14px] text-on-surface-variant"
						>arrow_forward</span
					>
					<span class="font-semibold text-primary">Review</span>
					<span class="material-symbols-outlined text-[14px] text-on-surface-variant"
						>arrow_forward</span
					>
					<span class="text-on-surface-variant">Checkout</span>
				</div>
			</div>
		</header>

		<!-- Loading -->
		<div v-if="isLoading" class="flex-1 flex items-center justify-center">
			<div class="space-y-4 text-center">
				<div
					class="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto"
				></div>
				<p class="text-body-md text-on-surface-variant">Loading pricing summary…</p>
			</div>
		</div>

		<!-- Error -->
		<div v-else-if="error" class="flex-1 flex items-center justify-center p-8">
			<div class="max-w-md text-center space-y-4">
				<div
					class="w-16 h-16 rounded-full bg-error-container/30 flex items-center justify-center mx-auto"
				>
					<span class="material-symbols-outlined text-error text-[32px]"
						>error_outline</span
					>
				</div>
				<p class="text-body-md text-on-surface">{{ error }}</p>
				<button
					class="px-6 py-2 rounded-full bg-primary text-on-primary font-semibold"
					@click="load"
				>
					Retry
				</button>
			</div>
		</div>

		<!-- Main -->
		<main v-else class="flex-1 pb-24">
			<div
				class="max-w-7xl mx-auto px-4 sm:px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8"
			>
				<!-- LEFT -->
				<div class="lg:col-span-7 space-y-6">
					<ReviewBookingSummary :booking="bookingInfo" />

					<!-- Appointments -->
					<div class="space-y-3">
						<h3
							class="text-headline-sm font-headline-sm text-on-surface flex items-center gap-2"
						>
							<span class="material-symbols-outlined text-primary text-[20px]"
								>event</span
							>
							Appointments
							<span
								class="ml-auto text-label-sm text-on-surface-variant font-normal"
							>
								{{ appointmentBreakdown.length }}
								{{
									appointmentBreakdown.length === 1
										? "appointment"
										: "appointments"
								}}
							</span>
						</h3>

						<div v-if="appointmentBreakdown.length" class="space-y-3">
							<ReviewAppointmentCard
								v-for="appt in appointmentBreakdown"
								:key="appt.appointmentId"
								:appointment="appt"
								:currency="currency"
								:coupon-draft="appointmentCouponDrafts[appt.appointmentId] ?? ''"
								:coupon-error="appointmentCouponErrors[appt.appointmentId] ?? ''"
								:is-applying="!!appointmentCouponBusy[appt.appointmentId]"
								:is-booking-coupon-active="areAppointmentCouponsLocked"
								@update:coupon-draft="
									store.setAppointmentCouponDraft(appt.appointmentId, $event)
								"
								@apply="store.applyAppointmentCoupon(appt.appointmentId)"
								@remove="store.removeAppointmentCoupon(appt.appointmentId)"
							/>
						</div>
						<div
							v-else
							class="rounded-xl border border-outline-variant/20 bg-surface p-6 text-center text-body-sm text-on-surface-variant"
						>
							No appointments found for this booking.
						</div>
					</div>

					<!-- Booking-level coupon -->
					<ReviewCouponSection
						:model-value="bookingCouponDraft"
						:applied-code="bookingCouponCode"
						:discount-amount="pricingSummary.bookingDiscountAmount"
						:currency="currency"
						:has-applied="!!bookingCouponCode"
						:is-applying="isApplyingBookingCoupon"
						:is-removing="isRemovingBookingCoupon"
						:error-message="bookingCouponError"
						:success-message="bookingCouponSuccess"
						:is-disabled="isBookingCouponLocked"
						@update:model-value="store.setBookingCouponDraft($event)"
						@apply="store.applyBookingCoupon()"
						@remove="store.removeBookingCoupon()"
					/>
				</div>

				<!-- RIGHT -->
				<div class="lg:col-span-5">
					<div class="lg:sticky lg:top-6 space-y-4">
						<ReviewPricingPanel :pricing="pricingSummary" :currency="currency" />

						<button
							:disabled="!canProceedToCheckout"
							class="w-full inline-flex items-center justify-center gap-2 px-8 py-3.5 rounded-full bg-primary text-on-primary font-semibold text-body-md hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
							@click="handleProceed"
						>
							<span class="material-symbols-outlined text-[20px]">lock</span>
							Proceed to Checkout
						</button>

						<p
							class="text-label-xs text-on-surface-variant text-center flex items-center justify-center gap-1"
						>
							<span class="material-symbols-outlined text-[14px]"
								>verified_user</span
							>
							Pricing is finalized before payment
						</p>
					</div>
				</div>
			</div>
		</main>

		<!-- Mobile footer -->
		<ReviewActionFooter
			class="lg:hidden fixed bottom-0 left-0 right-0 z-10"
			:final-amount="pricingSummary.finalAmount"
			:currency="currency"
			:can-proceed="canProceedToCheckout"
			:is-loading="false"
			@proceed="handleProceed"
		/>

		<!-- Strategy switch confirmation modal -->
		<Transition name="fade">
			<div
				v-if="pendingStrategySwitch"
				class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
				@click.self="store.cancelStrategySwitch()"
			>
				<div class="bg-surface rounded-2xl shadow-xl max-w-sm w-full p-6 space-y-4">
					<div class="flex items-center gap-3">
						<div
							class="w-10 h-10 rounded-full bg-warning-container/40 flex items-center justify-center shrink-0"
						>
							<span class="material-symbols-outlined text-warning text-[22px]"
								>swap_horiz</span
							>
						</div>
						<h3 class="text-headline-sm font-headline-sm text-on-surface">
							Switch Discount Strategy?
						</h3>
					</div>

					<p class="text-body-sm text-on-surface-variant">
						<template v-if="pendingStrategySwitch.type === 'booking'">
							This will remove all appointment-level discounts and apply a single
							booking coupon instead.
						</template>
						<template v-else>
							This will remove the booking-level coupon and apply a discount to a
							single appointment instead.
						</template>
					</p>

					<div class="flex gap-3 pt-1">
						<button
							class="flex-1 px-4 py-2.5 rounded-full border border-outline-variant text-body-sm font-semibold text-on-surface hover:bg-surface-container transition-colors"
							@click="store.cancelStrategySwitch()"
						>
							Cancel
						</button>
						<button
							class="flex-1 px-4 py-2.5 rounded-full bg-primary text-on-primary font-semibold text-body-sm hover:opacity-90 transition-opacity"
							@click="store.confirmStrategySwitch()"
						>
							Continue
						</button>
					</div>
				</div>
			</div>
		</Transition>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useBookingReviewStore } from "@/stores/bookingReview.store";
import ReviewBookingSummary from "@/components/review/ReviewBookingSummary.vue";
import ReviewAppointmentCard from "@/components/review/ReviewAppointmentCard.vue";
import ReviewCouponSection from "@/components/review/ReviewCouponSection.vue";
import ReviewPricingPanel from "@/components/review/ReviewPricingPanel.vue";
import ReviewActionFooter from "@/components/review/ReviewActionFooter.vue";

const route = useRoute();
const router = useRouter();
const store = useBookingReviewStore();

const {
	bookingInfo,
	pricingSummary,
	appointmentBreakdown,
	bookingCouponCode,
	bookingCouponDraft,
	bookingCouponError,
	bookingCouponSuccess,
	isApplyingBookingCoupon,
	isRemovingBookingCoupon,
	appointmentCouponDrafts,
	appointmentCouponErrors,
	appointmentCouponBusy,
	pendingStrategySwitch,
	isLoading,
	error,
} = storeToRefs(store);

const currency = computed(() => store.currency);
const canProceedToCheckout = computed(() => store.canProceedToCheckout);
const isBookingCouponLocked = computed(() => store.isBookingCouponLocked);
const areAppointmentCouponsLocked = computed(() => store.areAppointmentCouponsLocked);

const bookingId = computed(() => route.params.bookingId as string);

async function load() {
	if (bookingId.value) await store.fetchPricingSummary(bookingId.value);
}

function handleProceed() {
	if (!canProceedToCheckout.value) return;
	router.push({ name: "Checkout", params: { bookingId: bookingId.value } });
}

onMounted(load);
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}
</style>
