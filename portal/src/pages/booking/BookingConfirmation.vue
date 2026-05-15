<template>
	<ErrorMessage v-if="bookingError" :message="bookingError" class="m-4" />

	<div v-else-if="!isReady" class="flex-grow flex items-center justify-center p-4 sm:p-6 lg:p-8">
		<div class="text-slate-500 text-sm animate-pulse">Preparing your booking summary…</div>
	</div>

	<div v-else class="flex-grow p-4 sm:p-6 lg:p-8">
		<div class="mx-auto w-full max-w-5xl space-y-6">
			<div class="text-center space-y-4 py-4 sm:py-6">
				<div
					class="inline-flex items-center justify-center size-20 rounded-full bg-primary text-white shadow-glow mb-2"
				>
					<FeatherIcon class="h-10 font-medium" name="check" color="white" />
				</div>
				<div class="space-y-1">
					<h1 class="font-extrabold text-3xl sm:text-4xl text-slate-900 tracking-tight">
						Booking Summary
					</h1>
					<p class="text-lg text-slate-500">
						Review the appointments in this booking and complete payment when ready.
					</p>
				</div>
			</div>

			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<div class="lg:col-span-2 space-y-6">
					<div
						class="bg-white rounded-2xl shadow-soft border border-slate-100 p-6 sm:p-8 space-y-6"
					>
						<div
							class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4"
						>
							<div>
								<p
									class="text-xs uppercase tracking-widest text-slate-500 font-semibold mb-2"
								>
									Service Booking
								</p>
								<h2 class="text-2xl font-bold text-slate-900">
									{{ bookingResource.name }}
								</h2>
								<p class="text-sm text-slate-500 mt-1">
									{{ bookingResource.full_name || bookingResource.customer }}
									<span v-if="bookingResource.email"
										>• {{ bookingResource.email }}</span
									>
								</p>
							</div>
							<div class="text-right">
								<p
									class="text-xs uppercase tracking-widest text-slate-500 font-semibold"
								>
									Status
								</p>
								<p class="text-lg font-bold text-slate-900">
									{{ bookingResource.status }}
								</p>
							</div>
						</div>

						<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
							<div class="rounded-xl bg-slate-50 p-4">
								<p
									class="text-xs uppercase tracking-widest text-slate-500 font-semibold"
								>
									Booking Date
								</p>
								<p class="mt-2 text-sm font-semibold text-slate-900">
									{{ formattedBookingDate }}
								</p>
							</div>
							<div class="rounded-xl bg-slate-50 p-4">
								<p
									class="text-xs uppercase tracking-widest text-slate-500 font-semibold"
								>
									Total Amount
								</p>
								<p class="mt-2 text-sm font-semibold text-slate-900">
									{{ formatCurrency(totalAmount, bookingResource.currency) }}
								</p>
							</div>
							<div class="rounded-xl bg-slate-50 p-4">
								<p
									class="text-xs uppercase tracking-widest text-slate-500 font-semibold"
								>
									Outstanding
								</p>
								<p class="mt-2 text-sm font-semibold text-primary">
									{{ formatCurrency(totalDue, bookingResource.currency) }}
								</p>
							</div>
						</div>

						<div>
							<div class="flex items-center justify-between gap-3 mb-3">
								<h3 class="text-lg font-bold text-slate-900">
									Appointments in this booking
								</h3>
								<p class="text-sm text-slate-500">
									{{ bookingItems.length }} item{{
										bookingItems.length === 1 ? "" : "s"
									}}
								</p>
							</div>
							<div class="space-y-3">
								<div
									v-for="item in bookingItems"
									:key="`${item.service_type}-${
										item.idx || item.name || item.rate
									}`"
									class="rounded-xl border border-slate-200 p-4 flex items-start justify-between gap-4"
								>
									<div class="space-y-1">
										<p class="font-semibold text-slate-900">
											{{ item.service_type || "Service" }}
										</p>
										<p class="text-sm text-slate-500">
											{{ item.pricing_model || "Booking" }} • Qty
											{{ item.qty }}
										</p>
									</div>
									<p class="text-sm font-semibold text-slate-900">
										{{
											formatCurrency(
												item.total_amount,
												bookingResource.currency
											)
										}}
									</p>
								</div>
							</div>
						</div>

						<div>
							<div class="flex items-center justify-between gap-3 mb-3">
								<h3 class="text-lg font-bold text-slate-900">
									Linked appointments
								</h3>
							</div>
							<div
								class="overflow-hidden rounded-xl border border-slate-200 bg-slate-50/70"
							>
								<div
									v-if="bookingResource.appointment_list_html"
									v-html="bookingResource.appointment_list_html"
								></div>
								<div v-else class="p-4 text-sm text-slate-500">
									No linked appointments found yet.
								</div>
							</div>
						</div>
					</div>
				</div>

				<aside class="space-y-6">
					<div
						class="bg-white rounded-2xl shadow-soft border border-slate-100 p-6 sticky top-6"
					>
						<h2 class="text-lg font-bold text-slate-900 mb-4">Payment</h2>
						<div class="space-y-3 pb-4 border-b border-slate-100">
							<div class="flex justify-between text-sm">
								<span class="text-slate-500">Grand Total</span>
								<span class="font-semibold text-slate-900">{{
									formatCurrency(totalAmount, bookingResource.currency)
								}}</span>
							</div>
							<div class="flex justify-between text-sm">
								<span class="text-slate-500">Outstanding</span>
								<span class="font-semibold text-primary">{{
									formatCurrency(totalDue, bookingResource.currency)
								}}</span>
							</div>
						</div>

						<button
							v-if="canPay"
							@click="payNow"
							:disabled="paying"
							class="mt-5 w-full flex items-center justify-center gap-2 rounded-xl bg-primary hover:bg-primary/90 text-white font-bold py-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
							type="button"
						>
							<span
								v-if="paying"
								class="h-4 w-4 rounded-full border-2 border-white/40 border-t-white animate-spin"
							></span>
							<span>Pay Now</span>
						</button>

						<p
							v-else
							class="mt-5 text-sm text-emerald-700 font-medium bg-emerald-50 rounded-xl p-4"
						>
							This booking has been fully paid.
						</p>

						<div class="mt-4 flex flex-col gap-3">
							<router-link
								to="/bookings"
								class="text-sm text-slate-500 hover:text-primary font-medium transition-colors"
							>
								Back to Bookings
							</router-link>
							<router-link
								to="/"
								class="text-sm text-slate-500 hover:text-primary font-medium transition-colors"
							>
								Back to Home
							</router-link>
						</div>
					</div>
				</aside>
			</div>
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon, createDocumentResource, createResource, ErrorMessage } from "frappe-ui";
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { formatCurrency } from "@/utils";

const route = useRoute();
const bookingId = route.params.bookingId;
const paying = ref(false);

const bookingDocument = createDocumentResource({
	doctype: "Service Booking",
	name: bookingId,
	auto: true,
});

const paymentLinkResource = createResource({
	url: "frappoint.payments.get_payment_link",
	auto: false,
});

const bookingResource = computed(() => bookingDocument.doc || null);
const bookingError = computed(
	() => bookingDocument.error?.message || bookingDocument.error || null
);

const bookingItems = computed(() => bookingResource.value?.items || []);
const totalAmount = computed(() => Number(bookingResource.value?.grand_total || 0));
const totalDue = computed(() => Number(bookingResource.value?.outstanding_amount || 0));
const canPay = computed(() => totalDue.value > 0);

const isReady = computed(() => !!bookingResource.value);

const formattedBookingDate = computed(() => {
	if (!bookingResource.value?.booking_date) return "Not available";
	return new Intl.DateTimeFormat("en-US", {
		weekday: "long",
		year: "numeric",
		month: "short",
		day: "numeric",
	}).format(new Date(`${bookingResource.value.booking_date}T00:00:00`));
});

async function payNow() {
	if (!bookingResource.value || !canPay.value) return;

	paying.value = true;
	try {
		const redirectTo = window.location.href;
		const response = await paymentLinkResource.submit({
			reference_doctype: "Service Booking",
			reference_docname: bookingResource.value.name,
			payment_gateway: "",
			redirect_to: redirectTo,
		});

		if (typeof response === "string" && response) {
			window.location.href = response;
		}
	} catch (error) {
		console.error("Failed to create payment link:", error);
	} finally {
		paying.value = false;
	}
}
</script>
