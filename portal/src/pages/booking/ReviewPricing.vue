<template>
	<div class="min-h-screen bg-surface-bright">
		<main class="max-w-[1200px] mx-auto px-6 py-12">
			<div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
				<div>
					<nav class="flex items-center gap-2 mb-2">
						<router-link
							:to="{ name: 'Bookings' }"
							class="text-label-sm text-outline uppercase tracking-wider hover:text-primary transition-colors"
						>
							My Bookings
						</router-link>
						<span class="material-symbols-outlined text-[14px] text-outline"
							>chevron_right</span
						>
						<span class="text-label-sm text-primary font-bold uppercase tracking-wider"
							>Review &amp; Pricing</span
						>
					</nav>
					<h1 class="font-headline-lg text-headline-lg text-on-surface mb-2">
						Review Your Booking
					</h1>
					<p class="text-on-surface-variant font-body-md">
						Step 3 of 4 — Review appointments, apply coupons, then proceed to payment.
					</p>
				</div>
				<div class="flex items-center gap-4 font-label-md text-label-md">
					<span class="text-on-surface-variant">Cart</span>
					<span class="material-symbols-outlined text-[16px] text-outline"
						>arrow_forward</span
					>
					<span class="text-on-surface-variant">Guests</span>
					<span class="material-symbols-outlined text-[16px] text-outline"
						>arrow_forward</span
					>
					<span class="text-primary font-bold">Review</span>
					<span class="material-symbols-outlined text-[16px] text-outline"
						>arrow_forward</span
					>
					<span class="text-on-surface-variant">Checkout</span>
				</div>
			</div>

			<div v-if="isLoading" class="flex items-center justify-center py-24">
				<div class="space-y-4 text-center">
					<div
						class="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto"
					></div>
					<p class="text-body-md text-on-surface-variant">Loading pricing summary...</p>
				</div>
			</div>

			<div v-else-if="error" class="flex items-center justify-center py-24">
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

			<div v-else class="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
				<div class="lg:col-span-8 space-y-8">
					<div
						class="rounded-2xl border border-outline-variant/20 bg-white p-6 flex flex-col md:flex-row gap-8 items-center"
					>
						<div class="flex-1 space-y-1">
							<span class="text-label-sm text-outline uppercase tracking-widest"
								>Service Booking</span
							>
							<div class="flex items-center gap-3">
								<h2 class="font-headline-sm text-headline-sm text-on-surface">
									{{ bookingInfo.name }}
								</h2>
								<span
									class="px-3 py-1 rounded-full text-label-sm font-bold bg-tertiary-container/20 text-on-tertiary-container"
									>{{ bookingInfo.status || "Draft" }}</span
								>
							</div>
						</div>
						<div class="grid grid-cols-3 gap-8 text-center md:text-left">
							<div class="space-y-1">
								<span class="text-label-sm text-outline uppercase"
									>Appointments</span
								>
								<p class="font-headline-sm text-headline-sm text-on-surface">
									{{ bookingInfo.appointmentCount }}
								</p>
							</div>
							<div class="space-y-1">
								<span class="text-label-sm text-outline uppercase">Guests</span>
								<p class="font-headline-sm text-headline-sm text-on-surface">
									{{ bookingInfo.totalGuests }}
								</p>
							</div>
							<div class="space-y-1">
								<span class="text-label-sm text-outline uppercase">Currency</span>
								<p class="font-headline-sm text-headline-sm text-on-surface">
									{{ currency }}
								</p>
							</div>
						</div>
					</div>

					<div>
						<div class="flex items-center justify-between mb-4">
							<div class="flex items-center gap-2">
								<span class="material-symbols-outlined text-primary"
									>calendar_month</span
								>
								<h3 class="font-headline-sm text-headline-sm text-on-surface">
									Appointments
								</h3>
							</div>
							<span class="text-label-sm text-outline"
								>{{ appointmentBreakdown.length }}
								{{
									appointmentBreakdown.length === 1
										? "appointment"
										: "appointments"
								}}</span
							>
						</div>

						<div v-if="appointmentBreakdown.length" class="space-y-4">
							<div
								v-for="appt in appointmentBreakdown"
								:key="appt.appointmentId"
								class="rounded-2xl border border-outline-variant/20 bg-white overflow-hidden"
							>
								<div class="p-8">
									<div class="flex flex-col md:flex-row justify-between gap-6">
										<div class="space-y-4">
											<div class="space-y-1">
												<h4
													class="font-headline-sm text-headline-sm text-on-surface"
												>
													{{ appt.guestName || "Guest" }}
												</h4>
												<p
													class="text-primary font-label-md text-label-md"
												>
													{{ appt.serviceType }}
												</p>
											</div>
											<div
												class="flex flex-wrap gap-x-6 gap-y-2 text-on-surface-variant font-body-md"
											>
												<div
													v-if="appt.date"
													class="flex items-center gap-2"
												>
													<span
														class="material-symbols-outlined text-[20px]"
														>event</span
													>
													{{ formatDate(appt.date) }}
												</div>
												<div
													v-if="appt.startTime"
													class="flex items-center gap-2"
												>
													<span
														class="material-symbols-outlined text-[20px]"
														>schedule</span
													>
													{{ formatTime(appt.startTime)
													}}<template v-if="appt.endTime">
														– {{ formatTime(appt.endTime) }}</template
													>
												</div>
												<div
													v-if="appt.provider"
													class="flex items-center gap-2"
												>
													<span
														class="material-symbols-outlined text-[20px]"
														>tag</span
													>
													{{ appt.provider }}
												</div>
											</div>
										</div>
										<div class="text-right flex flex-col justify-end">
											<span
												class="text-label-sm text-outline uppercase tracking-wider block mb-1"
												>Appointment Total</span
											>
											<div class="flex flex-col items-end">
												<div
													class="flex justify-between w-full md:w-auto gap-12 border-b border-outline-variant/30 pb-1 mb-1"
												>
													<span class="text-on-surface-variant"
														>Base</span
													>
													<span class="text-on-surface font-medium">{{
														fmt(appt.baseAmount)
													}}</span>
												</div>
												<div
													v-if="appt.appointmentDiscountAmount > 0"
													class="flex justify-between w-full md:w-auto gap-12 border-b border-outline-variant/30 pb-1 mb-1"
												>
													<span class="text-on-surface-variant"
														>Discount</span
													>
													<span class="text-secondary font-medium"
														>-{{
															fmt(appt.appointmentDiscountAmount)
														}}</span
													>
												</div>
												<p
													class="font-headline-sm text-headline-sm text-primary font-bold"
												>
													{{ fmt(appt.finalAmount) }}
												</p>
											</div>
										</div>
									</div>

									<div class="mt-8 pt-6 border-t border-outline-variant/20">
										<div
											v-if="areAppointmentCouponsLocked"
											class="flex items-center gap-2 text-label-sm text-on-surface-variant"
										>
											<span class="material-symbols-outlined text-[16px]"
												>lock</span
											>
											Booking-level coupon active. Remove it to apply
											appointment coupon.
										</div>

										<div
											v-else-if="appt.appointmentCouponCode"
											class="flex items-center justify-between gap-3 bg-secondary-container/20 rounded-xl px-4 py-3"
										>
											<div class="flex items-center gap-2">
												<span
													class="material-symbols-outlined text-secondary text-[18px]"
													>check_circle</span
												>
												<span
													class="text-label-sm font-semibold text-on-surface"
													>{{ appt.appointmentCouponCode }}</span
												>
											</div>
											<button
												:disabled="
													!!appointmentCouponBusy[appt.appointmentId]
												"
												class="text-error font-label-sm hover:opacity-80 disabled:opacity-40"
												@click="
													store.removeAppointmentCoupon(
														appt.appointmentId
													)
												"
											>
												Remove
											</button>
										</div>

										<div v-else class="space-y-2">
											<button
												class="flex items-center gap-2 text-primary font-label-md text-label-md transition-all"
												@click="
													toggleAppointmentCoupon(appt.appointmentId)
												"
											>
												<span class="material-symbols-outlined">sell</span>
												Apply coupon to this appointment
												<span
													class="material-symbols-outlined transition-transform"
													:class="
														appointmentCouponOpen[appt.appointmentId]
															? 'rotate-180'
															: ''
													"
													>expand_more</span
												>
											</button>

											<div
												v-if="appointmentCouponOpen[appt.appointmentId]"
												class="mt-4"
											>
												<div class="flex flex-col sm:flex-row gap-3">
													<input
														:value="
															appointmentCouponDrafts[
																appt.appointmentId
															] ?? ''
														"
														class="w-full bg-surface-container-low border border-outline-variant rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all placeholder:text-outline/60 font-body-md"
														placeholder="Add coupon for this appointment"
														type="text"
														@input="
															store.setAppointmentCouponDraft(
																appt.appointmentId,
																($event.target as HTMLInputElement)
																	.value
															)
														"
														@keydown.enter.prevent="
															store.applyAppointmentCoupon(
																appt.appointmentId
															)
														"
													/>
													<button
														:disabled="
															!!appointmentCouponBusy[
																appt.appointmentId
															] ||
															!(
																appointmentCouponDrafts[
																	appt.appointmentId
																] ?? ''
															).trim()
														"
														class="bg-primary/10 text-primary border border-primary/20 px-8 py-3 rounded-xl font-label-md text-label-md hover:bg-primary hover:text-on-primary transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
														@click="
															store.applyAppointmentCoupon(
																appt.appointmentId
															)
														"
													>
														Apply
													</button>
												</div>
												<p
													v-if="
														appointmentCouponErrors[appt.appointmentId]
													"
													class="text-label-sm text-error mt-2 px-1"
												>
													{{
														appointmentCouponErrors[appt.appointmentId]
													}}
												</p>
											</div>
										</div>
									</div>
								</div>
							</div>
						</div>
						<div
							v-else
							class="rounded-xl border border-outline-variant/20 bg-surface p-6 text-center text-body-sm text-on-surface-variant"
						>
							No appointments found for this booking.
						</div>
					</div>

					<div class="pt-8 block md:hidden">
						<button
							:disabled="!canProceedToCheckout"
							class="w-full bg-primary text-on-primary rounded-2xl py-5 font-headline-sm text-headline-sm shadow-lg hover:opacity-95 transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-3"
							@click="handleProceed"
						>
							<span
								class="material-symbols-outlined"
								style="font-variation-settings: 'FILL' 1"
								>lock</span
							>
							Proceed to Checkout
						</button>
					</div>
				</div>

				<div class="lg:col-span-4 space-y-6 lg:sticky lg:top-28">
					<div
						class="rounded-2xl border border-outline-variant/20 bg-white p-8 space-y-8"
					>
						<h3 class="font-headline-sm text-headline-sm text-on-surface">
							Pricing Summary
						</h3>
						<div class="space-y-4 font-body-md text-body-md">
							<div class="flex justify-between items-center text-on-surface-variant">
								<span>Subtotal</span>
								<span class="font-medium text-on-surface">{{
									fmt(pricingSummary.subtotal)
								}}</span>
							</div>
							<div class="flex justify-between items-center text-on-surface-variant">
								<span>Discount</span>
								<span
									:class="
										discountTotal > 0
											? 'font-medium text-secondary'
											: 'font-medium text-on-surface'
									"
								>
									-{{ fmt(discountTotal) }}
								</span>
							</div>
							<div
								class="pt-4 border-t border-outline-variant/30 flex justify-between items-center"
							>
								<span class="font-headline-sm text-headline-sm text-on-surface"
									>Total Payable</span
								>
								<span
									class="font-headline-sm text-headline-sm text-primary font-bold"
									>{{ fmt(pricingSummary.finalAmount) }}</span
								>
							</div>
						</div>

						<div class="pt-6 border-t border-outline-variant/30 space-y-4">
							<div class="flex items-center gap-2">
								<span class="material-symbols-outlined text-outline"
									>confirmation_number</span
								>
								<span class="font-label-md text-label-md text-on-surface-variant"
									>Have a Booking Coupon?</span
								>
							</div>

							<div
								v-if="isBookingCouponLocked"
								class="rounded-xl bg-surface-container-low border border-outline-variant/30 px-4 py-3 text-label-sm text-on-surface-variant"
							>
								Appointment-level discounts are active. Remove them to apply a
								booking coupon.
							</div>

							<div
								v-else-if="bookingCouponCode"
								class="rounded-xl bg-secondary-container/20 border border-secondary/30 px-4 py-3 flex items-center justify-between gap-3"
							>
								<div>
									<p class="font-label-md text-on-surface">
										{{ bookingCouponCode }}
									</p>
									<p class="text-label-sm text-on-surface-variant">
										Coupon applied
									</p>
								</div>
								<button
									:disabled="isRemovingBookingCoupon"
									class="text-error font-label-sm hover:opacity-80 disabled:opacity-40"
									@click="store.removeBookingCoupon()"
								>
									Remove
								</button>
							</div>

							<div v-else class="flex flex-col gap-3">
								<input
									:value="bookingCouponDraft"
									class="w-full bg-surface-container-low border border-outline-variant rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all placeholder:text-outline/60 font-body-md"
									placeholder="Enter coupon code"
									type="text"
									@input="
										store.setBookingCouponDraft(
											($event.target as HTMLInputElement).value
										)
									"
									@keydown.enter.prevent="store.applyBookingCoupon()"
								/>
								<button
									:disabled="
										isApplyingBookingCoupon || !bookingCouponDraft.trim()
									"
									class="w-full bg-secondary-container text-on-secondary-container border border-secondary/20 px-6 py-3 rounded-xl font-label-md text-label-md hover:bg-secondary hover:text-on-secondary transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
									@click="store.applyBookingCoupon()"
								>
									Apply Coupon
								</button>
							</div>

							<p v-if="bookingCouponError" class="text-label-sm text-error">
								{{ bookingCouponError }}
							</p>
							<p v-if="bookingCouponSuccess" class="text-label-sm text-secondary">
								{{ bookingCouponSuccess }}
							</p>
						</div>

						<div class="space-y-4 pt-4">
							<button
								:disabled="!canProceedToCheckout"
								class="w-full bg-primary text-on-primary rounded-2xl py-4 font-label-md text-label-md shadow-md hover:opacity-95 transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-3"
								@click="handleProceed"
							>
								<span
									class="material-symbols-outlined"
									style="font-variation-settings: 'FILL' 1"
									>lock</span
								>
								Proceed to Checkout
							</button>
							<div
								class="flex items-center justify-center gap-2 text-label-sm text-outline"
							>
								<span class="material-symbols-outlined text-[16px]">verified</span>
								Pricing is finalized before payment
							</div>
						</div>
					</div>
				</div>
			</div>

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
		</main>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useBookingReviewStore } from "@/stores/bookingReview.store";
import { formatCurrency } from "@/utils";

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
const discountTotal = computed(
	() =>
		Number(pricingSummary.value.appointmentDiscountTotal || 0) +
		Number(pricingSummary.value.bookingDiscountAmount || 0)
);

const bookingId = computed(() => route.params.bookingId as string);
const appointmentCouponOpen = ref<Record<string, boolean>>({});

async function load() {
	if (bookingId.value) await store.fetchPricingSummary(bookingId.value);
}

function handleProceed() {
	if (!canProceedToCheckout.value) return;
	router.push({ name: "Checkout", params: { bookingId: bookingId.value } });
}

function toggleAppointmentCoupon(appointmentId: string) {
	appointmentCouponOpen.value = {
		...appointmentCouponOpen.value,
		[appointmentId]: !appointmentCouponOpen.value[appointmentId],
	};
}

function fmt(amount: number) {
	return formatCurrency(Number(amount || 0), currency.value);
}

function formatDate(dateStr: string) {
	if (!dateStr) return "";
	try {
		return new Date(dateStr).toLocaleDateString(undefined, {
			weekday: "short",
			month: "short",
			day: "numeric",
		});
	} catch {
		return dateStr;
	}
}

function formatTime(timeStr: string) {
	if (!timeStr) return "";
	try {
		const [h, m] = timeStr.split(":");
		const d = new Date();
		d.setHours(Number(h), Number(m));
		return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
	} catch {
		return timeStr;
	}
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
